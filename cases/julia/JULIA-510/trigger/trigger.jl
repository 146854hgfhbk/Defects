using Test
import MathOptInterface as MOI
println("JULIA-TRIGGER-START")
@testset "JULIA-510 deep nonlinear canonicalization" begin
    x = MOI.VariableIndex(1)
    g = MOI.ScalarNonlinearFunction(:^, Any[1.0 * x + 1.0 * x, 2])
    for _ in 1:100_000
        g = MOI.ScalarNonlinearFunction(:sin, Any[g])
    end
    @test !MOI.Utilities.is_canonical(g)
    MOI.Utilities.canonicalize!(g)
    h = MOI.ScalarNonlinearFunction(:^, Any[2.0 * x, 2])
    for _ in 1:100_000
        h = MOI.ScalarNonlinearFunction(:sin, Any[h])
    end
    @test MOI.Utilities.is_canonical(h)
    @test isapprox(g, h)
end
