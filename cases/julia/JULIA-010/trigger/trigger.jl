using Test
using GLM

println("JULIA-TRIGGER-START")
@testset "weighted negative-binomial fit" begin
    data = (
        count=[0, 0, 0, 1, 1, 2, 2, 3, 10, 15, 20, 30],
    )
    weights = [0.8, 1.2, 0.9, 1.1, 0.8, 1.2, 0.9, 1.1, 0.8, 1.2, 0.9, 1.1]
    model = negbin(
        @formula(count ~ 1),
        data,
        LogLink();
        wts=weights,
        initialθ=2.0,
    )
    @test length(coef(model)) == 1
    @test isfinite(deviance(model))
    @test isfinite(loglikelihood(model))
end
