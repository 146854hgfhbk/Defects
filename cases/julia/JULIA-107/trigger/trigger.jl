using Test
using StatsModels

println("JULIA-TRIGGER-START")
@testset "contrast types must be instantiated" begin
    data = (y=rand(6), x=[:b, :a, :c, :a, :a, :b])
    formula = @formula(y ~ x)
    @test_throws ArgumentError schema(formula, data, Dict(:x => DummyCoding))
end
