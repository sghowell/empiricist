# Primary-source audit

Reviewed 2026-09-05. Equation labels below refer to the specified arXiv versions.
The certificate pins this dictionary and its implementation, not downloaded PDF
bytes. Runtime replay requires no network. Published quantum-field statements
remain trusted, explicitly identified inputs to the written proof.

| Source | Exact input and role |
| --- | --- |
| [Fewster--Kontou, 1809.05047v2](https://arxiv.org/pdf/1809.05047v2) | Section I fixes FK signature/Einstein conventions. Eqs. (19)--(20), (23)--(28) specify Leibniz-compatible stress and the conserved Hadamard prescription. Eq. (31) defines EED. The identical `P,H` on the radiation patch allows a common derivative-Wick prescription. |
| [Fewster--Kontou, 2108.12668v1](https://arxiv.org/pdf/2108.12668v1) | Section 2 lists the four finite stress ambiguities `m^4*g,m^2*G,I,J`. Definition 2.1 and Eq. (13) distinguish an actual SEE solution from a fixed-background calculation. |
| [Pinamonti, 0806.0803v2](https://arxiv.org/pdf/0806.0803v2) | Lemma 2.5 gives the scalar-curvature-dependent coincidence correction under conformal transport; Eq. (9) gives the Wick-square freedom `alpha*R`. With both scalar curvatures zero, the transported Minkowski vacuum has zero Wick square for every such choice. No convention-sensitive nonzero coefficient is needed here. |
| [Carlson--Anderson, 1607.01699v5](https://arxiv.org/pdf/1607.01699v5) | Eq. (2.1) fixes `(-+++)`. Eqs. (2.4)--(2.7) give the conformal-vacuum density as an explicitly subtracted mode integral plus local curvature. Eqs. (2.9a,b) give the `R^2` and Weyl-squared variations, which vanish on this patch. |
| [Glavan--Prokopec--Prymidis, 1308.5954v1](https://arxiv.org/pdf/1308.5954v1) | Independent **minimal-field** route. Eqs. (1)--(3), (12), (26), (29) fix metric, action, covariant stress and physical density/pressure. Radiation modes (40) and result (41) match this checkpoint. Appendix A, (121)--(122), provides independent conformal-time anomaly and finite-counterterm expressions. |

## Exact source equations used by the computational interfaces

Write `K=a'/a` for the conformal Hubble rate and `H=adot/a` for the physical
one; neither is an extrinsic-curvature symbol in this directory.

Carlson--Anderson:

`rho = hbar/(4*pi^2*a^2)*integral_0^infinity k^2*(|psidot|^2+(k/a)^2*|psi|^2-k/a^2) dk + rho_local`,

`rho_local = hbar/(2880*pi^2)*[-H1_tt/6+3*H^4]`,

`H1_tt = -36*H*Hddot+18*Hdot^2-108*Hdot*H^2`.

Glavan--Prokopec--Prymidis, radiation specialization:

`u_R=exp(-i*k/K)/sqrt(2*k)`; since `K=1/eta`, it is our rescaled mode.

`rho_R=hbar*K^4/(960*pi^2*a^4)`,
`p_R=hbar*K^4/(576*pi^2*a^4)`.

The Appendix A anomaly terms, after dividing covariant conformal components by
`a^2`, are

`rho_CA = hbar*(2*K''*K-K'^2)/(2880*pi^2*a^4)`
`         +3*alpha_CA*(2*K''*K-K'^2-3*K^4)/a^4`,

`p_CA = -hbar*(2*K'''-2*K''*K+K'^2)/(8640*pi^2*a^4)`
`       +alpha_CA*(-2*K'''+2*K''*K-K'^2+12*K'*K^2-3*K^4)/a^4`.

The independent rational implementation differentiates `K=eta^-1` itself,
then checks both finite `alpha_CA` coefficients vanish. It also compares the
remaining physical stress to the separate proper-time route.

## Deliberate exclusions

Do not use the inflation-matched radiation stress from the later sections of
1308.5954: that is a different state. Do not turn a source trace formula into
an energy density without its signature dictionary and its integration
constant. Do not remove the anomaly by treating an on-shell classical identity
as an identity of all renormalized Wick products. Do not regard a tensor
conserved only on conformally flat backgrounds as a freely adjustable locally
covariant counterterm on all spacetimes.
