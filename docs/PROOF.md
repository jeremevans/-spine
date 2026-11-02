# Why the splines are mathematically equivalent

## Claim and assumptions

Let each coordinate axis contain at least four **distinct increasing real
nodes**, and let a finite real value be given at every point of their Cartesian
product. The tensor product of one-dimensional, interpolating, C²,
**not-a-knot cubic splines** is unique. Any implementation satisfying those
conditions constructs the same real-valued function on the grid domain.

This establishes mathematical equivalence of the specified algorithms. It does
not establish bit-for-bit equality of floating-point programs or certify an
unexecuted MATLAB release. Numerical evidence is recorded separately in
[RESULTS.md](RESULTS.md). MATLAB's `cubic` convolution, natural splines, FMM
endpoint rules, smoothing splines, and scattered-data splines are outside this
claim. Use MATLAB/Octave **`spline`** and SciPy **`cubic`**.

## 1. Construct the one-dimensional spline

Number the nodes from 0 to n−1. Write

$$h_i=x_{i+1}-x_i>0,\qquad
\delta_i=\frac{y_{i+1}-y_i}{h_i},\qquad M_i=s''(x_i).$$

On interval i, set t=x−x_i and

$$s_i(x)=y_i+
\left(\delta_i-\frac{h_i(2M_i+M_{i+1})}{6}\right)t+
\frac{M_i}{2}t^2+\frac{M_{i+1}-M_i}{6h_i}t^3.$$

This interpolates both endpoints and gives the assigned second derivatives.
Matching first derivatives at each interior node gives

$$h_{i-1}M_{i-1}+2(h_{i-1}+h_i)M_i+h_iM_{i+1}
=6(\delta_i-\delta_{i-1}),\quad i=1,\ldots,n-2.$$

Not-a-knot requires the third derivatives of the first two pieces to agree,
and likewise those of the last two:

$$-h_1M_0+(h_0+h_1)M_1-h_0M_2=0,$$

$$-h_{n-2}M_{n-3}+(h_{n-3}+h_{n-2})M_{n-2}
-h_{n-3}M_{n-1}=0.$$

Thus we have n linear equations in n unknown second derivatives. These are the
equations implemented independently in `reference.py`.

## 2. Prove that the solution is unique

Eliminate M₀ using the first endpoint equation. The first remaining row, for
M₁ and M₂, has diagonal coefficient

$$D=\frac{(h_0+h_1)(h_0+2h_1)}{h_1}$$

and off-diagonal coefficient

$$E=\frac{(h_0+h_1)(h_1-h_0)}{h_1}.$$

Since h₀,h₁>0, we have h₀+2h₁>|h₁−h₀|, hence **D>|E|**.
Eliminating Mₙ₋₁ gives the reflected, strictly dominant last row.
Every other remaining row is strictly diagonally dominant because

$$2(h_{i-1}+h_i)>h_{i-1}+h_i.$$

The reduced square matrix is therefore strictly diagonally dominant. To see
directly why it is nonsingular, suppose Az=0 with a nonzero z and choose a row k
where |zₖ| is maximal. Its equation would imply

$$|a_{kk}|\,|z_k|
\leq\sum_{j\ne k}|a_{kj}|\,|z_j|
\leq\left(\sum_{j\ne k}|a_{kj}|\right)|z_k|
<|a_{kk}|\,|z_k|,$$

a contradiction. There is exactly one vector of second derivatives, and the
interval formula then gives exactly one spline. The argument includes n=4,
where the reduced matrix is 2×2 and the result is a single global cubic.

This is a proof for **arbitrary positive interval widths and arbitrary real
data**, not a conclusion inferred from a collection of examples.

## 3. Extend the proof to any number of dimensions

The one-dimensional interpolation map is linear in the data. Let ℓⱼ,ᵢ be the
unique not-a-knot spline on axis j whose nodal values are 1 at node i and 0
at the other nodes. These cardinal splines form a basis of its spline space:
the nodal evaluation map is a bijection by the uniqueness result above.

For a D-dimensional grid, define

$$S(q_1,\ldots,q_D)=
\sum_{i_1,\ldots,i_D}V_{i_1\ldots i_D}
\prod_{j=1}^{D}\ell_{j,i_j}(q_j).$$

The products form a basis of the tensor-product spline space. Evaluating S at
the grid nodes returns V because each cardinal factor is a Kronecker delta.
Consequently, interpolation in that tensor-product space is unique.

Applying the one-dimensional maps along successive axes evaluates this same
sum. Axis order does not change it in exact arithmetic: operations on distinct
tensor dimensions commute. Alternatively, if Aⱼ is a one-dimensional B-spline
collocation matrix, the multidimensional coefficient system has a Kronecker
product matrix (with ordering determined by vectorization). Its inverse is the
Kronecker product of the Aⱼ inverses. Sequential solves and the full system
therefore produce the same function.

The theorem covers arbitrary finite D. The delivered executable tests cover
1D–4D; that finite test coverage is a separate statement.

## 4. Connect the theorem to the named software

| Implementation | Connection to the theorem |
| --- | --- |
| MATLAB `interpn(...,'spline')` | MathWorks explicitly documents not-a-knot endpoint conditions and tensor-product cubic interpolation. |
| Octave `interpn(...,'spline')` | The N-D spline implementation applies one-dimensional `spline` along axes; the default endpoint condition is not-a-knot. |
| SciPy `RegularGridInterpolator(method='cubic')` | It constructs a tensor-product degree-three B-spline. SciPy 1.17.0's `make_ndbspl` explicitly uses not-a-knot conditions in each dimension. |
| This R wrapper | It builds cardinal weights with `pracma::interp1(method='spline')` and contracts them with the data tensor. The package documents MATLAB-compatible splines. |
| Independent reference | It solves the second-derivative equations derived above and evaluates their tensor products; it does not call SciPy interpolation. |

The implication is conditional on the software implementing its stated
mathematical contract. The source/documentation mapping establishes that
contract; runtime tests check the particular installed implementations.
The R wrapper is explicit project code, **not a claim that base R has a
drop-in N-dimensional `interpn` function**.

## 5. An exact worked example

Use axes x=[0,1,2,4,7], y=[−2,0,1,3,4,6] and a 5×6 value matrix

$$V_{ij}=\frac{10+((i+2)(j+3)\bmod 11)}{100},
\quad i=0,\ldots,4,\ j=0,\ldots,5.$$

The fixture is arbitrary positive synthetic data; it is not sampled from a
global cubic polynomial. Exact rational arithmetic gives:

| Query (x,y) | Exact spline value | Decimal approximation |
| --- | --- | --- |
| (1.5, 0.5) | 838733 / 5632000 | 0.14892276278409092 |
| (3.25, 2.5) | 2031089 / 13926400 | 0.14584451114430147 |
| (6.75, 5.5) | 10632481 / 69632000 | 0.15269532686121323 |

`scripts/verify.py` regenerates 36 such exact answers using Python's standard
`fractions.Fraction`, verifies 200 rational interpolation/continuity/endpoint
equalities, and compares complete one-dimensional polynomial coefficient
arrays with `CubicSpline`. These exact checks validate the construction on this
fixture; the general uniqueness proof is in sections 1–3.

## 6. Floating-point and domain qualifications

Different bases, solve orders, and arithmetic produce different rounding. We
use SciPy's direct `spsolve` to make coefficient-solve error small on these
fixtures. An iterative solver has an additional stopping tolerance. A direct
solve is not a universal accuracy or performance guarantee, especially for
ill-conditioned grids or large tensor systems.

All main cross-engine cases use explicit NaN or numeric fills outside the
domain. The theorem's claim is on the closed grid domain. The Python unit suite
also tests boundary-polynomial extrapolation against the independent reference;
that does not establish cross-engine extrapolation equivalence. Default
extrapolation behavior differs among APIs.

The common adapter contract excludes missing input values, complex data,
descending or duplicate axes, fewer than four nodes per axis, and trailing data
pages. MATLAB has small-grid fallbacks that SciPy's N-D cubic API does not.

Positive inputs can yield a negative cubic spline. Consequently, taking a real
log after interpolation requires an explicit positivity check. This is a
property of the common spline, not a language-porting error.

See [SOURCES.md](SOURCES.md) for primary documentation and source locations.
