import inspect, unittest
import numpy as np
from emitted_state.emitter import EmissionResult, WaveformEvent, simulate_hh_piecewise
from emitted_state.gate_c0 import PRIMARY_ARMS,SECONDARY_ARMS,ArmSet,EventTable,GateC0Protocol,arm_features,availability_index,build_event_table,deranged_waveforms,emitter_current,event_identity_sha256,fit_forecasters,fit_timing_stats,passive_state_for_observed,residualize_waveforms

class GateC0DatasetTests(unittest.TestCase):
    @staticmethod
    def _table(seed,n=12,constant=False):
        return EventTable(seed,np.arange(n)+8,np.arange(n)*10.0+100,np.arange(n)*10.0+104,np.arange(n)+20,np.ones((n,8)) if constant else np.arange(n*8,dtype=float).reshape(n,8)/10+1,np.ones((n,4))*2 if constant else np.arange(n*4,dtype=float).reshape(n,4)/20,np.ones(n)*0.5,np.tile(np.arange(12.0),(n,1)),np.tile(np.arange(19.0),(n,1)),{"boundary":0,"overlap":0,"undefined_feature":0,"missing_eight_isi":0})
    def test_frozen_emitter_drive_and_availability_index(self):
        p=GateC0Protocol(); np.testing.assert_allclose(emitter_current(np.array([-1.,0.,1.]),0,1,p),10+4*np.tanh(np.array([-.5,0,.5])),rtol=0,atol=1e-15); self.assertEqual([availability_index(x) for x in (4,4.001,4.999,5)],[4,5,5,5])
    def test_timing_context_uses_invalid_waveform_predecessor_onsets(self):
        p=GateC0Protocol(observe=100); on=np.array([0,1,3,6,10,15,21,28,36,45.]); e=WaveformEvent(9,45,49,np.array([1.,2.,3.,4.])); em=EmissionResult(on,(e,),{"boundary":0,"overlap":0,"undefined_feature":1}); t=build_event_table(10,np.linspace(-1,1,100),np.zeros((100,19)),em,p); np.testing.assert_allclose(t.timing_raw[0],np.log([9,8,7,6,5,4,3,2])); self.assertEqual(t.event_ids[0],9)
    def test_arm_set_preserves_identity_and_widths(self):
        t=self._table(123); m,s=fit_timing_stats({123:t}); a=arm_features(t,m,s,np.zeros((12,4)),GateC0Protocol()); self.assertIsInstance(a,ArmSet); [self.assertEqual(a.features[k].shape,(12,12)) for k in PRIMARY_ARMS]; [self.assertEqual(a.features[k].shape,(12,19 if k=="internal_cable_state" else 12)) for k in SECONDARY_ARMS]; np.testing.assert_array_equal(a.event_ids,t.event_ids); self.assertEqual(event_identity_sha256(a),event_identity_sha256(a))
    def test_deranged_waveforms_preserve_rows_without_fixed_points(self):
        w=np.arange(200.).reshape(50,4); a=deranged_waveforms(w,500123); np.testing.assert_array_equal(a,deranged_waveforms(w,500123)); self.assertTrue(np.all(np.any(a!=w,axis=1))); self.assertEqual(sorted(map(tuple,a.tolist())),sorted(map(tuple,w.tolist())))
    def test_residualization_provenance_is_trajectory_separated(self):
        tr={s:self._table(s,8,True) for s in (10,11,12,13,14,15)}; te={s:self._table(s,8,True) for s in (100,101)}; m,sc=fit_timing_stats(tr); rtr,rte,p=residualize_waveforms(tr,te,m,sc,.001); alltr=set(tr)
        for s in tr:self.assertEqual(set(p["train"][s]),alltr-{s}); self.assertTrue(np.all(np.isfinite(rtr[s])))
        for s in te:self.assertEqual(set(p["test"][s]),alltr); self.assertTrue(np.all(np.isfinite(rte[s])))
    def test_fit_interfaces_do_not_accept_hidden_or_clean_truth(self):
        self.assertEqual(set(inspect.signature(fit_forecasters).parameters),{"features_by_arm","targets","ridge_factor"}); rp=set(inspect.signature(residualize_waveforms).parameters); [self.assertNotIn(x,rp) for x in ("targets","forecast_targets","clean_truth","hidden","hidden_state")]
    def test_no_spike_single_spike_and_constant_columns_are_finite(self):
        p=GateC0Protocol(observe=30); obs=np.zeros(30); pas=np.zeros((30,19)); t0=build_event_table(10,obs,pas,EmissionResult(np.array([]),tuple(),{"boundary":0,"overlap":0,"undefined_feature":0}),p); self.assertEqual(t0.event_ids.size,0); one=EmissionResult(np.array([10.]),(WaveformEvent(0,10,14,np.ones(4)),),{"boundary":0,"overlap":0,"undefined_feature":0}); t1=build_event_table(10,obs,pas,one,p); self.assertEqual(t1.exclusions["missing_eight_isi"],1)
        tr={s:self._table(s,6,True) for s in (10,11)}; te={100:self._table(100,6,True)}; m,sc=fit_timing_stats(tr); rr,_,_=residualize_waveforms(tr,te,m,sc,.001); a=arm_features(tr[10],m,sc,rr[10],GateC0Protocol()); models=fit_forecasters(a.features,np.ones(6),.001); [self.assertTrue(np.all(np.isfinite(model.predict(a.features[k])))) for k,model in models.items()]
    def test_future_observed_change_does_not_change_completed_passive_state_or_event(self):
        p=GateC0Protocol(observe=80); obs=np.sin(np.linspace(0,4,80)); ch=obs.copy(); ch[41:]+=1000; mean=float(obs.mean()); scale=float(obs.std()); a=passive_state_for_observed(obs,mean,scale,p); b=passive_state_for_observed(ch,mean,scale,p); np.testing.assert_allclose(a[:41],b[:41],rtol=0,atol=1e-12); sm=float(a[:,0].mean()); ss=float(a[:,0].std()); ta,va=simulate_hh_piecewise(emitter_current(a[:,0],sm,ss,p)); _,vb=simulate_hh_piecewise(emitter_current(b[:,0],sm,ss,p)); np.testing.assert_allclose(va[ta<=40],vb[ta<=40],rtol=0,atol=1e-12)

if __name__=='__main__':unittest.main()
