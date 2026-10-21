using Test
using GLM
using Random

println("JULIA-TRIGGER-START")
@testset "Logistic regression residual degrees of freedom" begin
    num_rows = 100
    x1 = randn(MersenneTwister(123), num_rows)
    x2 = randn(MersenneTwister(1234), num_rows)
    x3 = 2 * x1 + 3 * x2
    response = Int.(randn(MersenneTwister(12345), num_rows) .> 0)
    design = hcat(ones(num_rows), x1, x2, x3)
    model = fit(GeneralizedLinearModel, design, response, Binomial(), LogitLink();
                dropcollinear=true)
    @test dof_residual(model) == 97
end
