using Test
using Optim
using LinearAlgebra

println("JULIA-TRIGGER-START")
@testset "trust-region hard-case KKT step" begin
    H = Matrix(Diagonal([-2.0, 1.0]))
    gradient = [0.0, 1.0]
    step = zeros(2)
    model, interior, lambda, hard_case, reached_solution =
        Optim.solve_tr_subproblem!(gradient, H, 1.0, step)
    @test hard_case
    @test !interior
    @test reached_solution
    @test abs(lambda - 2.0) < 1e-12
    @test abs(norm(step) - 1.0) < 1e-12
    @test abs(step[2] + 1 / 3) < 1e-12
    @test abs(abs(step[1]) - sqrt(8.0) / 3) < 1e-12
    @test abs(model - (-7 / 6)) < 1e-12
    @test norm((H + lambda * I) * step + gradient) < 1e-10
end
