using BasicBSpline

# Minimal regression from issue #214 / PR #215. Integer knot endpoints
# previously selected an integer accumulator and raised InexactError.
P = BSplineSpace{3}(KnotVector(1:12))
result = BasicBSpline.innerproduct_R(t -> t, (P,))

@assert result ≈ collect(3:10)
