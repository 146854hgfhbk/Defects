using Test
using SciMLBase

println("JULIA-TRIGGER-START")

f1! = (du, u, p, t) -> (du .= u)
f2! = (du, u, p, t) -> (du .= -u)
u0 = [1.0, 2.0]
sf = SplitFunction(f1!, f2!)
@test sf._func_cache === nothing
@test_throws ArgumentError sf(similar(u0), u0, nothing, 0.0)

# On the buggy source this leaves _func_cache as nothing and the call below
# reaches get_tmp(nothing, du).  The constructed fixed state allocates it.
prob = ODEProblem(sf, u0, (0.0, 1.0))
@test prob.f._func_cache !== nothing
du = zeros(2)
prob.f(du, u0, nothing, 0.0)
@test du ≈ zeros(2)

println("JULIA-055 SplitFunction trigger completed")
