# State-Bearing Pings and Readout Heads

## A computational analogy between contextual Transformer activations, spike-waveform state, and synaptic readout

**Working manuscript — 2026-10-01**  
**Repository:** `BrainAsInverseModelerV3`

## Abstract

A spike is commonly abstracted as an event time: a neuron either emitted an action potential or it did not. A token in a Transformer is likewise a discrete event at a position, but the token identity alone is not the computational state carried forward by the network. The same token in two contexts occupies different activation states in the residual stream, and downstream components respond to projections of those contextual states. This paper develops a deliberately limited analogy: an emitted neuronal spike may also be better represented as an **event plus a small state-dependent shape**, and a synapse may be understood computationally as a **readout of that shape**.

The analogy is motivated by two results in `BrainAsInverseModelerV3`. Gate A found that a passive dendritic cable retained useful predictive state internally, while a declared scalar soma-history output failed to expose enough of that state to beat the current observation. Gate C0 then held spike timing fixed across primary comparisons and asked whether the waveform of each emitted spike added useful predictive information. It did. At the frozen primary condition, timing-only prediction gave mean NRMSE 0.7641; timing plus the real waveform gave 0.6873; and timing plus the component of waveform residualized against recent spike timing gave 0.6554. Real waveform beat timing-only and a dimension-matched shuffled-waveform control on the same 4/4 held-out trajectories. The timing-residualized waveform also beat timing-only on 4/4. An independent Gaussian-label control remained chance-like. Raw observed-input delays were still better than every spike-derived representation, so this is not a claim that waveform coding is an optimal memory scheme.

The combined result suggests a computational decomposition:

$$
\text{history-bearing state}
\rightarrow
\text{active emission transform}
\rightarrow
(\text{event time},\text{event shape})
\rightarrow
\text{receiver-specific readout}.
$$

This resembles, at an abstract architectural level, the Transformer pattern in which a discrete token position carries a contextual activation vector that downstream heads read through learned projections. The claim is **not** that neurons are Transformers or that synapses are attention heads. The useful commonality is narrower: **state can be encoded geometrically in the form of an event, and what survives downstream depends on the reader.** Existing physiology makes the final step plausible but unresolved: presynaptic action-potential waveform can alter calcium influx and neurotransmitter release, but Gate C0 did not model an axon, terminal, synapse, postsynaptic neuron, or biological learning rule. The next decisive experiment is therefore not another decoder on waveform features. It is a transmission test: whether same-time, different-history spikes produce reliably different downstream synaptic effects.

---

## 1. From binary events to state-bearing events

The standard point-process abstraction of a spike train records event times

$$
\mathcal{S}=\{t_1,t_2,\ldots,t_n\}.
$$

This abstraction is extraordinarily useful. Rate codes, temporal codes, population codes, point-process models, and most spiking neural networks can be built from it. But it makes one strong compression decision in advance: two spikes occurring at the same time are treated as the same transmitted object regardless of the ionic and voltage trajectory that generated them.

A richer representation is

$$
p_k=(t_k,w_k),
$$

where $t_k$ is the event time and $w_k$ is a small waveform-state vector. In Gate C0,

$$
w_k=
[
\text{peak amplitude},
\text{half-height width},
\text{peak sharpness},
\text{repolarization slope}
].
$$

The important distinction is that $w_k$ is not appended arbitrarily. It emerges from the active state of the emitter. Different histories can drive the same neuron to emit events at comparable times while leaving different conductance states, adaptation states, membrane trajectories, and therefore different waveforms.

Recent empirical work gives this premise biological motivation. Martin-Burgos et al. report that within-neuron action-potential waveform variability is state dependent rather than merely random: waveform features covary with input drive and aspects of surrounding network state, and contain information not captured by a binary-spike description [1]. This does not by itself demonstrate that downstream neurons decode such waveform variability. It establishes the narrower premise needed here: **the emitted action potential can reflect recent state**.

Gate C0 asks the corresponding computational question: if timing is held fixed, is that state-bearing shape useful to a receiver?

The answer in the frozen synthetic mechanism was yes.

---

## 2. What Gate A and Gate C0 jointly establish

### 2.1 Gate A: state can exist without being readable at the output

Gate A used the passive V3 dendritic cable and asked whether a receiver restricted to causal soma-voltage history could forecast later observed $x$ values. At zero input noise and horizon 20:

| Representation | Mean NRMSE ↓ |
|---|---:|
| Raw input delays | **0.6406** |
| Internal cable state | **0.7441** |
| Present input | 0.8160 |
| Soma history | 0.8314 |
| Instantaneous soma | 0.9492 |

The internal cable state predicted the future better than the current observation, so useful history-dependent information remained inside the sender. Yet the declared soma-history output failed its predeclared criterion. The result separated two propositions that are easy to conflate:

1. **The sender contains useful state.**
2. **The output channel makes that state readable downstream.**

Gate A supported the first and failed the second under its declared output/readout.

This distinction is central. Observability is not a property of internal dynamics alone. It depends on the internal state, the output map, the temporal sampling of that output, and the receiver.

### 2.2 Gate C0: the active emission transform exposes additional state

Gate C0 preserved the passive sender and added a one-way classical Hodgkin–Huxley emitter. Every primary receiver saw the **same spike events, onset times, and decision times**. The only difference was which description of those same events was made available.

At zero noise and horizon 20:

| Receiver information | Mean NRMSE ↓ | Mean R² ↑ |
|---|---:|---:|
| Raw observed-input delays | **0.6301** | **0.5911** |
| Timing + residual waveform | **0.6554** | **0.5569** |
| Timing + real waveform | **0.6873** | **0.5128** |
| Internal cable state | 0.7483 | 0.4229 |
| Timing only | 0.7641 | 0.3980 |
| Timing + shuffled waveform | 0.7774 | 0.3768 |
| Current observed input | 0.8187 | 0.3094 |
| Waveform only | 0.8960 | 0.1731 |

The predeclared criteria passed:

- **C0-A:** timing + real waveform beat timing-only and shuffled waveform in mean NRMSE and beat both on the same 4/4 held-out trajectories.
- **C0-B:** timing + timing-residualized waveform beat timing-only in mean NRMSE and on 4/4 held-out trajectories.
- The independent Gaussian-label control remained chance-like: mean NRMSE 1.0453 and mean $R^2=-0.0417$.

The shuffled control matters because it preserves the dimensionality and distribution of waveform vectors while destroying the event-specific pairing. Its failure means the gain was not obtained merely by handing the reader four additional numbers.

The result can therefore be stated narrowly:

> In this synthetic mechanism, **how a spike is shaped contains useful predictive information that is not exhausted by when the spike occurred**.

That is stronger than a correlation between waveform and inter-spike interval. It is still much weaker than a claim of a general biological waveform code.

---

## 3. The Transformer correspondence: same symbol, different contextual state

The useful Transformer analogy begins with a distinction between **symbol identity** and **contextual activation**.

A token is discrete. But a Transformer does not carry only token identity through its layers. At each position it maintains a high-dimensional activation in the residual stream. Downstream components read projections of that activation and write new contributions back into the stream [2,3]. The activation of the same lexical token can therefore differ substantially with context.

The simplest example is:

### Same token, different context

$$
\text{``bank''}+\text{river context}\rightarrow h_A
$$

$$
\text{``bank''}+\text{money context}\rightarrow h_B.
$$

The discrete token is the same. The contextual state is not.

Gate C0 suggests an analogous neuronal object:

### Same event time, different history

$$
t_k+\text{history A}\rightarrow w_A
$$

$$
t_k+\text{history B}\rightarrow w_B.
$$

Again, the coarse event description can be the same while the state attached to that event differs.

This motivates the shared abstraction

$$
\boxed{\text{event identity or address}+\text{context-dependent state}}.
$$

For a Transformer position, the state is a vector in the residual stream. For a spike, the state is more naturally a short **trajectory** through voltage and conductance space. The four Gate C0 waveform features are only a low-dimensional projection of that trajectory.

The analogy should therefore not be read as “a spike is a token.” The more precise correspondence is:

| Transformer | Neuronal emission |
|---|---|
| discrete token/position | spike event/time |
| contextual residual activation $h_t$ | state-dependent waveform trajectory $W_k(\tau)$ |
| projection/read by downstream component | biophysical sensitivity of downstream terminal/synapse |
| representation depends on prior context | waveform depends on prior cellular/input state |
| useful subspaces depend on reader | useful waveform directions may depend on receiver physiology |

The shared computational principle is that the **event label alone is an impoverished description of the transmitted state**.

---

## 4. Residual-stream geometry and waveform geometry

Elhage et al. describe the Transformer residual stream as a communication channel into which components write and from which later components read through projections [2]. A crucial feature of this picture is that a representation does not have to be meaningful coordinate-by-coordinate. What matters is whether a downstream transformation is sensitive to the relevant direction or subspace.

Toy models of superposition make the geometric point even more explicitly: neural networks can organize features as directions in a shared representational space, with interference and accessibility depending on geometry and nonlinear readout [4]. We do **not** need the stronger claim that biological waveform space implements Transformer superposition. The useful lesson is simply that **information accessibility is reader-dependent and coordinate-dependent**.

Gate C0 contains a small version of this phenomenon.

Let the waveform vector be $w_k$, and let $c_k$ be recent spike-timing context. Gate C0 constructs a timing-predictable component $\hat w(c_k)$ using training data and then forms

$$
w_k^{\perp}=w_k-\hat w(c_k).
$$

The timing-residualized representation performed better than the raw waveform representation:

$$
\text{timing + raw waveform}: 0.6873
$$

$$
\text{timing + residual waveform}: 0.6554.
$$

Nothing in this operation creates new physical information. It changes the coordinates presented to a fixed reader. The conservative interpretation is therefore geometric:

> waveform state was more useful after a timing-correlated component was removed, suggesting that the fixed reader could access the remaining state-dependent variation more easily in that basis.

This matters beyond Gate C0. It suggests a general separation:

$$
\boxed{\text{information present}\neq\text{information easily readable}}.
$$

A channel may contain a distinction that one receiver ignores and another amplifies. A representation can preserve state while placing it in a direction poorly matched to the reader.

This is exactly why the identity of the downstream mechanism matters.

---

## 5. The synapse as the readout head

The phrase **“the synapse is the readout head”** is deliberately an analogy, not a biological equivalence.

In a Transformer, a downstream component can be described as applying learned projections to a contextual activation. In the simplest abstract form,

$$
y=R h,
$$

where $h$ is the contextual representation and $R$ selects or transforms directions useful for the next computation.

A biological synapse does not multiply a residual vector by a learned matrix. But it is also not a passive counter of spike timestamps. The presynaptic terminal contains voltage-gated calcium channels, ion channels, release machinery, vesicle pools, and nonlinear calcium-to-release coupling. These mechanisms can make transmitter release sensitive to details of the presynaptic action-potential trajectory.

This sensitivity is established experimentally in several preparations. Sabatini and Regehr showed that broadening the presynaptic spike at the granule-cell-to-Purkinje-cell synapse increased calcium influx and strongly increased synaptic strength [5]. Hoppa et al. showed that presynaptic action-potential waveform at small CNS terminals is actively regulated and linked to calcium-channel abundance and release probability [6]. Chao and Yang showed that action-potential waveform controls the timing and magnitude of presynaptic calcium current at the calyx of Held [7]. Reviews of axonal physiology likewise treat activity-dependent shaping of the presynaptic action potential as a mechanism capable of modulating transmitter release [8].

These findings justify a concrete transfer function

$$
r_k=F_{\text{synapse}}\left(W_k(\tau),s_k\right),
$$

where $W_k(\tau)$ is the incoming spike waveform and $s_k$ is the current synaptic state.

The key idea is not that the synapse “decodes a message” symbolically. It is that the synapse may **physically project waveform state into release state**.

Under this view, a neuronal network can communicate using a sequence of transformations:

$$
\text{dendritic/history state}
\rightarrow
\text{ionic emitter state}
\rightarrow
\text{spike waveform}
\rightarrow
\text{Ca}^{2+}/\text{release}
\rightarrow
\text{postsynaptic state}.
$$

The readout is implemented by physics.

This is the point at which the Transformer analogy becomes most useful. In both systems, the receiver need not reconstruct the sender’s entire internal state. It only needs to be sensitive to the directions that matter for its own computation.

---

## 6. Address plus payload

A compact way to describe the proposed code is

$$
p_k=(t_k,w_k).
$$

The spike time $t_k$ acts as an **address or event coordinate**. The waveform state $w_k$ acts as a **small payload**.

This does not imply that waveform is independent of timing. Gate C0 explicitly shows that part of waveform is predictable from recent timing. The point is conditional:

$$
I(\text{future};w_k\mid\text{timing context})>0
$$

under the synthetic protocol, operationalized by the held-out forecasting advantage of waveform-augmented receivers over timing-only controls.

This representation suggests a different way to think about spike-based communication. The neuron need not send a high-dimensional replica of its dendritic state. It may compress a large internal state

$$
x_t\in\mathbb{R}^{D}
$$

into a much smaller event payload

$$
w_k\in\mathbb{R}^{d},\qquad d\ll D,
$$

provided that $w_k$ preserves distinctions useful to downstream receivers.

That is closer to a **sufficient statistic** than a full state dump.

Gate C0 does not prove that biology performs such an optimal compression. It demonstrates only that an active emitter can create a small state-bearing payload with measurable downstream utility under an external decoder.

---

## 7. Why Gate A makes Gate C0 more informative

The positive Gate C0 result would be less interesting without the negative Gate A result.

Gate A showed that the internal cable state was predictive, but a simple scalar soma-history representation did not expose enough of that advantage. This created a concrete output-bottleneck problem:

$$
\text{useful internal state}\not\Rightarrow\text{useful emitted representation}.
$$

Gate C0 then inserted an active nonlinear output transform rather than merely widening the soma-history window. The result suggests that spike generation itself can act as a **state-dependent compression transform**:

$$
\Phi:\text{internal trajectory}\rightarrow(\text{spike time},\text{waveform state}).
$$

The combined lesson is therefore not “dendrites compute and spikes transmit it all.” It is more constrained:

1. the sender can contain useful history-dependent state;
2. a particular output coordinate can fail to expose it;
3. an active output transform can expose a different, small predictive projection;
4. whether that projection matters biologically depends on the downstream receiver.

This sequence turns “information in the neuron” into an observability problem rather than a storage claim.

---

## 8. Testable predictions

The analogy is useful only if it generates experiments that can fail. Several follow directly.

### 8.1 Same-time, different-history transmission

Construct or identify pairs of spikes with nearly identical event timing but different preceding histories. Measure whether the resulting presynaptic waveforms differ and, crucially, whether those waveform differences produce different calcium transients, release probabilities, or postsynaptic responses.

The decisive comparison is

$$
(t_k,\text{history A})\rightarrow w_A\rightarrow r_A
$$

versus

$$
(t_k,\text{history B})\rightarrow w_B\rightarrow r_B.
$$

If $w_A\neq w_B$ but $r_A\approx r_B$ across relevant biological conditions, the “synapse as readout head” idea loses force.

### 8.2 Receiver-specific projections

Different synapse types should be sensitive to different waveform directions because they express different voltage-gated channels, calcium-channel complements, coupling distances, release machinery, and short-term plasticity states.

The same presynaptic waveform difference could therefore matter strongly at one terminal and weakly at another.

This is analogous only in the abstract sense to different computational heads reading different subspaces from the same representation.

### 8.3 Waveform basis matters

If raw waveform features mix timing-related and state-related variation, a biologically relevant transformation may isolate more useful coordinates. Candidate coordinates include derivative features, phase-plane trajectories, sodium/potassium gating proxies, afterhyperpolarization structure, and calcium-channel-relevant voltage integrals.

A strong test would compare equal-information transformations of the same waveform and ask whether downstream predictability or synaptic effect changes substantially.

### 8.4 Full waveform should beat hand-selected features if the trajectory matters

Gate C0 uses only four engineered waveform features. If state truly lives in the trajectory, a carefully controlled receiver given the full waveform should recover distinctions missed by those summaries. Conversely, if four features saturate the useful information, the “latent geometry” picture should be narrowed accordingly.

### 8.5 The information should survive transmission

The central unresolved gate is

$$
I(\text{future};\text{postsynaptic response}\mid\text{spike timing})>0.
$$

A waveform result that vanishes after realistic axonal propagation, presynaptic calcium dynamics, stochastic release, and postsynaptic filtering would remain interesting cellular physiology but would not support a useful network-level state-bearing-ping architecture.

---

## 9. What the Transformer analogy does and does not buy us

The analogy contributes three useful ideas.

First, it separates **event identity** from **contextual state**. A token identity is not its residual activation; a spike timestamp need not be its complete emitted state.

Second, it emphasizes **reader dependence**. A representation is useful only relative to operations capable of reading it. The existence of information in a waveform does not imply that every synapse can use it.

Third, it encourages us to study **geometry rather than individual scalar features**. A waveform may carry state in combinations or trajectories that are not interpretable one coordinate at a time.

But the analogy has strict limits.

Transformers use explicitly parameterized linear projections, attention patterns, residual addition, normalization, and learned weights. Biological neurons use ion-channel kinetics, cable filtering, stochastic vesicle release, receptor dynamics, plasticity, and morphology. A synapse is therefore not an attention head, a spike is not a token, and membrane voltage is not a residual stream.

The correspondence is architectural:

> **context-dependent state is attached to an event, and a downstream mechanism selects which aspects of that state affect the next computation.**

Nothing stronger is required for the analogy to be useful.

---

## 10. Limitations of the present evidence

The empirical evidence in this repository is synthetic and intentionally narrow.

The passive cable and the Hodgkin–Huxley emitter are illustrative mechanisms, not fitted biological cells. The soma-to-emitter current map is artificial and fixed. The emitter is one compartment. Gate C0 does not model axonal propagation, terminal morphology, voltage-gated calcium channels, vesicle release, stochastic synaptic transmission, a postsynaptic neuron, or plasticity.

The forecasting receiver is an external supervised quadratic ridge model trained against delayed observed $x$. No claim is made that a biological synapse learns or implements that decoder.

The Transformer comparison is conceptual, not mechanistic evidence.

Most importantly, explicit raw input history still outperformed every spike-derived representation at the primary horizon:

$$
\text{raw delays}=0.6301
<
\text{timing + residual waveform}=0.6554.
$$

The result therefore does **not** show that state-bearing spikes are a superior memory architecture. It shows that **the active emission transform preserves a useful distinction beyond spike timing**.

That is the claim boundary.

---

## 11. Conclusion

The simplest abstraction of neural communication is a sequence of spike times. Gate C0 suggests that, even in a small synthetic system, this abstraction can discard useful state carried by the detailed form of the event itself.

The resulting computational picture is:

$$
\boxed{
\text{history}
\rightarrow
\text{resident state}
\rightarrow
\text{state-bearing ping}
\rightarrow
\text{receiver-specific projection}
}
$$

The Transformer analogy sharpens what this means. The same discrete token can carry different contextual activations; the same coarse spike event can carry different waveform states. Downstream computation depends not merely on the existence of the event but on what the receiver can read from the state attached to it.

This leads to the central proposal of this paper:

> **Treat a spike not only as a timestamp, but as an event carrying a small context-dependent physical state; treat the synapse not only as a counter of events, but as a receiver whose biophysics selects a projection of that state.**

Or, in the deliberately compact analogy:

> **The synapse is the readout head.**

The phrase should remain an analogy until the missing transmission experiment is done. The next decisive result would be to show that two same-time spikes produced by different histories not only have different shapes, but drive systematically different downstream synaptic states. If that survives realistic transmission and appropriate timing controls, “state-bearing pings” would become more than a representation metaphor: they would describe a concrete physical channel by which a neuron exposes a compressed trace of its internal history to the network.

---

## References

1. Martin-Burgos, B., Juavinett, A., Riviere, P. D., Hammonds, R., & Voytek, B. (2026). **Action potential waveforms are state-dependent.** bioRxiv preprint 2026.09.15.751814. https://doi.org/10.64898/2026.09.15.751814
2. Elhage, N., Nanda, N., Olsson, C., et al. (2021). **A Mathematical Framework for Transformer Circuits.** Transformer Circuits Thread. https://transformer-circuits.pub/2021/framework/index.html
3. Vaswani, A., Shazeer, N., Parmar, N., et al. (2017). **Attention Is All You Need.** *Advances in Neural Information Processing Systems 30*. https://arxiv.org/abs/1706.03762
4. Elhage, N., Hume, T., Olsson, C., et al. (2022). **Toy Models of Superposition.** arXiv:2209.10652. https://arxiv.org/abs/2209.10652
5. Sabatini, B. L., & Regehr, W. G. (1997). **Control of Neurotransmitter Release by Presynaptic Waveform at the Granule Cell to Purkinje Cell Synapse.** *Journal of Neuroscience*, 17(10), 3425–3435. https://doi.org/10.1523/JNEUROSCI.17-10-03425.1997
6. Hoppa, M. B., Gouzer, G., Armbruster, M., & Ryan, T. A. (2014). **Control and Plasticity of the Presynaptic Action Potential Waveform at Small CNS Nerve Terminals.** *Neuron*, 84(4), 778–789. https://doi.org/10.1016/j.neuron.2014.09.038
7. Chao, O. Y., & Yang, Y.-M. (2019). **Timing constraints of action potential evoked Ca²⁺ current and transmitter release at a central nerve terminal.** *Scientific Reports*, 9, 4448. https://doi.org/10.1038/s41598-019-41120-5
8. Debanne, D., Campanac, E., Bialowas, A., Carlier, E., & Alcaraz, G. (2011). **Axon Physiology.** *Physiological Reviews*, 91(2), 555–602. https://doi.org/10.1152/physrev.00048.2009

## Repository evidence

- Gate A findings: [`docs/findings.md`](findings.md)
- Gate C0 findings: [`docs/gate_c0_findings.md`](gate_c0_findings.md)
- Gate A receipt: [`results/gate_a_receipt.json`](../results/gate_a_receipt.json)
- Gate C0 receipt: [`results/gate_c0_receipt.json`](../results/gate_c0_receipt.json)