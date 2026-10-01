"""Gate C0 event-centric waveform-state forecasting controls."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib

import numpy as np

from .cable import make_cable
from .emitter import EmissionResult
from .readout import QuadraticReadout
from .world import delay_features

PRIMARY_ARMS=("timing_only","timing_real_waveform","timing_shuffled_waveform","timing_residual_waveform")
SECONDARY_ARMS=("waveform_only","current_observed_input","raw_input_delays","internal_cable_state")
ALL_ARMS=PRIMARY_ARMS+SECONDARY_ARMS

@dataclass(frozen=True)
class GateC0Protocol:
    train_seeds:tuple[int,...]=(10,11,12,13,14,15); test_seeds:tuple[int,...]=(100,101,102,103); burn:int=1000; observe:int=4000; horizons:tuple[int,...]=(1,5,20); noise_levels:tuple[float,...]=(0.0,0.02); world_dt:float=0.01; cable_dt_ms:float=1.0; drive_na:float=0.01; ridge_factor:float=0.001; emitter_dt_ms:float=0.025; emitter_bias:float=10.0; emitter_gain:float=4.0; emitter_tanh_scale:float=2.0; waveform_pre_ms:float=1.0; waveform_post_ms:float=4.0; timing_size:int=8; feature_width:int=12; min_primary_events:int=50; shuffle_seed_base:int=500000; negative_label_seed_base:int=700000

@dataclass(frozen=True)
class EventTable:
    seed:int; event_ids:np.ndarray=field(repr=False); onset_ms:np.ndarray=field(repr=False); availability_ms:np.ndarray=field(repr=False); availability_index:np.ndarray=field(repr=False); timing_raw:np.ndarray=field(repr=False); waveform:np.ndarray=field(repr=False); current_observed:np.ndarray=field(repr=False); raw_input_delays:np.ndarray=field(repr=False); internal_cable_state:np.ndarray=field(repr=False); exclusions:dict[str,int]

@dataclass(frozen=True)
class ArmSet:
    event_ids:np.ndarray=field(repr=False); onset_ms:np.ndarray=field(repr=False); availability_ms:np.ndarray=field(repr=False); features:dict[str,np.ndarray]=field(repr=False)

def _finite_vector(x,name):
    arr=np.asarray(x,dtype=float)
    if arr.ndim!=1 or not np.all(np.isfinite(arr)): raise ValueError(f"{name} must be a finite vector")
    return arr

def passive_state_for_observed(observed,observed_mean,observed_scale,protocol):
    signal=_finite_vector(observed,"observed")
    if not np.isfinite(observed_mean) or not np.isfinite(observed_scale) or observed_scale<=0: raise ValueError("observed normalization must be finite with positive scale")
    normalized=(signal-observed_mean)/observed_scale; cable=make_cable(diverse=True); currents=protocol.drive_na*normalized[:,None]*np.ones((1,len(cable.ports))); return cable.encode(currents,protocol.cable_dt_ms)

def emitter_current(soma,soma_mean,soma_scale,protocol):
    soma=_finite_vector(soma,"soma")
    if not np.isfinite(soma_mean) or not np.isfinite(soma_scale) or soma_scale<=0: raise ValueError("soma normalization must be finite with positive scale")
    z=(soma-soma_mean)/soma_scale; return protocol.emitter_bias+protocol.emitter_gain*np.tanh(z/protocol.emitter_tanh_scale)

def availability_index(availability_ms,interval_ms=1.0):
    if not np.isfinite(availability_ms) or availability_ms<0 or not np.isfinite(interval_ms) or interval_ms<=0: raise ValueError
    ratio=availability_ms/interval_ms; rounded=round(ratio); return int(rounded) if abs(ratio-rounded)<=1e-12 else int(np.ceil(ratio))

def _empty_event_table(seed,exclusions): return EventTable(int(seed),np.empty(0,dtype=int),np.empty(0),np.empty(0),np.empty(0,dtype=int),np.empty((0,8)),np.empty((0,4)),np.empty(0),np.empty((0,12)),np.empty((0,19)),exclusions)

def build_event_table(seed,observed,passive_state,emission,protocol):
    observed=_finite_vector(observed,"observed"); passive=np.asarray(passive_state,dtype=float)
    if passive.shape!=(observed.size,19) or not np.all(np.isfinite(passive)): raise ValueError("passive_state must have shape (time, 19) and be finite")
    onsets=_finite_vector(emission.onset_times_ms,"onset_times_ms")
    if np.any(np.diff(onsets)<=0): raise ValueError("onset_times_ms must be strictly increasing")
    exclusions=dict(emission.exclusions); exclusions.setdefault("boundary",0); exclusions.setdefault("overlap",0); exclusions.setdefault("undefined_feature",0); exclusions["missing_eight_isi"]=0; exclusions["availability_boundary"]=0
    all_delays=delay_features(observed,size=protocol.feature_width,stride=1); rows=[]
    for event in emission.events:
        j=int(event.spike_index)
        if j<protocol.timing_size: exclusions["missing_eight_isi"]+=1; continue
        if j>=onsets.size or not np.isclose(onsets[j],event.onset_ms,rtol=0.0,atol=1e-9): raise ValueError("event spike_index/onset does not match full onset sequence")
        isi=np.array([onsets[j-k]-onsets[j-k-1] for k in range(protocol.timing_size)],dtype=float)
        if np.any(isi<=0) or not np.all(np.isfinite(isi)): raise ValueError("inter-spike intervals must be finite and positive")
        a_idx=availability_index(event.availability_ms,protocol.cable_dt_ms)
        if a_idx<0 or a_idx>=observed.size: exclusions["availability_boundary"]+=1; continue
        feature=np.asarray(event.features,dtype=float)
        if feature.shape!=(4,) or not np.all(np.isfinite(feature)): raise ValueError("waveform features must be a finite four-vector")
        rows.append((j,float(event.onset_ms),float(event.availability_ms),a_idx,np.log(isi),feature,float(observed[a_idx]),all_delays[a_idx].copy(),passive[a_idx].copy()))
    if not rows:
        if protocol.timing_size!=8 or protocol.feature_width!=12: raise ValueError("Gate C0 timing_size/feature_width must remain 8/12")
        return _empty_event_table(seed,exclusions)
    return EventTable(int(seed),np.array([r[0] for r in rows],dtype=int),np.array([r[1] for r in rows]),np.array([r[2] for r in rows]),np.array([r[3] for r in rows],dtype=int),np.stack([r[4] for r in rows]),np.stack([r[5] for r in rows]),np.array([r[6] for r in rows]),np.stack([r[7] for r in rows]),np.stack([r[8] for r in rows]),exclusions)

def eligible_rows(table,horizon,observe):
    if not isinstance(horizon,(int,np.integer)) or horizon<=0 or not isinstance(observe,(int,np.integer)) or observe<=0: raise ValueError
    return np.flatnonzero(table.availability_index+int(horizon)<int(observe))

def fit_timing_stats(train_tables):
    if not train_tables: raise ValueError("train_tables must be nonempty")
    parts=[t.timing_raw for t in train_tables.values() if t.timing_raw.shape[0]>0]
    if not parts: raise ValueError("no training timing rows available")
    timing=np.concatenate(parts,axis=0); mean=timing.mean(axis=0); scale=timing.std(axis=0); scale[scale<1e-12]=1.0; return mean,scale

def deranged_waveforms(waveform,seed):
    waveform=np.asarray(waveform,dtype=float)
    if waveform.ndim!=2 or waveform.shape[1]!=4 or not np.all(np.isfinite(waveform)): raise ValueError("waveform must be a finite (n,4) matrix")
    n=waveform.shape[0]
    if n<2:return waveform.copy()
    rng=np.random.default_rng(int(seed)); base=np.arange(n)
    for _ in range(10000):
        perm=rng.permutation(n)
        if np.all(perm!=base): return waveform[perm].copy()
    return waveform[np.roll(base,1)].copy()

def _normalized_timing(table,mean,scale):
    mean=np.asarray(mean,dtype=float); scale=np.asarray(scale,dtype=float)
    if mean.shape!=(8,) or scale.shape!=(8,) or np.any(scale<=0): raise ValueError("timing mean/scale must be positive width-eight vectors")
    return (table.timing_raw-mean)/scale

def residualize_waveforms(train_tables,test_tables,timing_mean,timing_scale,ridge_factor):
    if len(train_tables)<2: raise ValueError("at least two training trajectories are required")
    train_residuals={}; provenance={"train":{},"test":{}}; train_seeds=tuple(sorted(train_tables))
    for held_seed in train_seeds:
        fit_seeds=tuple(s for s in train_seeds if s!=held_seed); x=np.concatenate([_normalized_timing(train_tables[s],timing_mean,timing_scale) for s in fit_seeds]); y=np.concatenate([train_tables[s].waveform for s in fit_seeds]); model=QuadraticReadout(ridge_factor).fit(x,y); train_residuals[held_seed]=train_tables[held_seed].waveform-model.predict(_normalized_timing(train_tables[held_seed],timing_mean,timing_scale)); provenance["train"][held_seed]=list(fit_seeds)
    x=np.concatenate([_normalized_timing(train_tables[s],timing_mean,timing_scale) for s in train_seeds]); y=np.concatenate([train_tables[s].waveform for s in train_seeds]); model=QuadraticReadout(ridge_factor).fit(x,y); test_residuals={}
    for seed in sorted(test_tables): test_residuals[seed]=test_tables[seed].waveform-model.predict(_normalized_timing(test_tables[seed],timing_mean,timing_scale)); provenance["test"][seed]=list(train_seeds)
    return train_residuals,test_residuals,provenance

def arm_features(table,timing_mean,timing_scale,residual_waveform,protocol):
    timing=_normalized_timing(table,timing_mean,timing_scale); residual=np.asarray(residual_waveform,dtype=float)
    if residual.shape!=table.waveform.shape or not np.all(np.isfinite(residual)): raise ValueError
    n=table.event_ids.size; zero4=np.zeros((n,4)); zero8=np.zeros((n,8)); current=np.zeros((n,protocol.feature_width));
    if n: current[:,0]=table.current_observed
    features={"timing_only":np.column_stack([timing,zero4]),"timing_real_waveform":np.column_stack([timing,table.waveform]),"timing_shuffled_waveform":np.column_stack([timing,deranged_waveforms(table.waveform,protocol.shuffle_seed_base+int(table.seed))]),"timing_residual_waveform":np.column_stack([timing,residual]),"waveform_only":np.column_stack([zero8,table.waveform]),"current_observed_input":current,"raw_input_delays":table.raw_input_delays.copy(),"internal_cable_state":table.internal_cable_state.copy()}
    return ArmSet(table.event_ids.copy(),table.onset_ms.copy(),table.availability_ms.copy(),features)

def event_identity_sha256(arm_set):
    h=hashlib.sha256()
    for arr in (arm_set.event_ids,arm_set.onset_ms,arm_set.availability_ms):
        a=np.ascontiguousarray(arr); h.update(str(a.dtype).encode("ascii")); h.update(np.asarray(a.shape,dtype=np.int64).tobytes()); h.update(a.tobytes())
    return h.hexdigest()

def fit_forecasters(features_by_arm,targets,ridge_factor):
    targets=np.asarray(targets,dtype=float)
    if targets.ndim!=1 or targets.size==0 or not np.all(np.isfinite(targets)): raise ValueError
    models={}
    for key,values in features_by_arm.items():
        x=np.asarray(values,dtype=float)
        if x.ndim!=2 or x.shape[0]!=targets.size or not np.all(np.isfinite(x)): raise ValueError
        models[key]=QuadraticReadout(ridge_factor).fit(x,targets)
    return models
