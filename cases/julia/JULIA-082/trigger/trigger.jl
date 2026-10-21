using Test
using SciMLBase
using ConstructionBase: setproperties

println("JULIA-TRIGGER-START")
@testset "ODESolution property replacement preserves state metadata" begin
    f = (u, p, t) -> nothing
    prob = ODEProblem(f, nothing, (0.0, 1.0))
    sol = SciMLBase.build_solution(
        prob, :NoAlgorithm, [0.0, 1.0], [nothing, nothing]; interp=nothing
    )
    @test sol isa ODESolution{Any,2}
    updated = setproperties(sol, (retcode=ReturnCode.Success,))
    @test typeof(updated) === typeof(sol)
    @test updated.u === sol.u
    @test updated.retcode == ReturnCode.Success
    no_saved_states = setproperties(sol, (u=nothing,))
    @test no_saved_states isa ODESolution{Any,2}
    @test no_saved_states.u === nothing
end
