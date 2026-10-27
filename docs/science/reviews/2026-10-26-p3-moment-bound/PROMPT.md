You are an independent referee for a short new result in linear quantum optics. Work read-only and do not modify any file.

The claim is about any Bell-state measurement on two dual-rail photonic qubits that uses a passive linear-optical interferometer U in U(m), an ancilla state of exactly k photons (any pure or mixed state on the ancilla modes), photon-number-resolving detection, and any unambiguous assignment of detection patterns to Bell states. For every such scheme, the average success probability over the four Bell states satisfies p_avg <= (k+1)/(k+2), and hence so does the minimum over the four Bell states.

The statement, the five-step proof and its consequences are in docs/science/2026-10-26-p3-moment-bounds.md (section "The proof"). The machine-checked parts are the following:
- src/empiricist/certificates/p3_moment.py, an exact SOS certificate of the one-body lemma;
- src/empiricist/certificates/p3_moment_check.py, exact moment identities at (k, m) = (0, 4), (1, 5) and (1, 6);
- the claim files claims/P3.one_body_usd_lemma.yaml, claims/P3.k0_m4_p_avg_upper_bound.yaml, claims/P3.k1_m5_p_avg_upper_bound.yaml, claims/P3.k1_m6_p_avg_upper_bound.yaml and claims/P3.moment_bound_general_k.yaml, with their evidence in claims/evidence/p3_moment/.
The open problem P3 is stated in docs/open_problems_ftfbqc.md.

Tasks:

1. Check the proof line by line as a referee would, and try hard to break it. In particular, check:
   (a) the definitions of success and of an unambiguous assignment, and whether they match the standard notion in the literature (Calsamiglia and Lutkenhaus 2001; Grice 2011; Ewert and van Loock 2014);
   (b) the moment identity of Step 3, including the vanishing of cross terms between signal and ancilla modes and between the rails of the two signal qubits, for ancilla states that are entangled across modes or mixed;
   (c) the one-body lemma and its dual operator Y;
   (d) the photon-number sums of Step 5;
   (e) any hidden assumption, such as indistinguishability, the dual-rail encoding, the transpose, normalization, or patterns with several photons in one mode.
   Look for a scheme in the literature that exceeds (k+1)/(k+2) for some k while using only passive linear optics, k ancilla photons and photon-number-resolving detection.

2. Search the literature with web search for any earlier statement of this bound or an equivalent one. The target is upper bounds on ancilla-assisted linear-optical Bell measurement as a function of the number of ancilla photons. Look at least at work by Calsamiglia and Lutkenhaus, Lutkenhaus-Calsamiglia-Suominen, Vaidman-Yoran, Carollo-Palma, Grice, Ewert and van Loock, Olivo and Grosshans, Wein et al., Bayerbach et al., Bartolucci et al., and any work from 2020 to 2026. For anything close, give the exact reference and statement. Say whether it subsumes, implies or differs from this bound.

3. Check each consequence stated in the note: p*_avg(2) = 3/4; 1 - p*(k) >= 1/(k+2) for every k, for both the average and the minimum metric; 1 - p*_avg(k) = Theta(1/k); and p_avg <= 2/3 at k = 1. Say whether each follows, and name any assumption it needs, such as monotonicity in k.

4. Check that the claim texts in claims/P3.*.yaml say no more than their evidence supports.

Report a verdict on correctness (correct, correct with gaps, or incorrect). List every gap or error with its severity, the literature findings with full references, and your assessment of novelty. Write the report as your final message, in Markdown.
