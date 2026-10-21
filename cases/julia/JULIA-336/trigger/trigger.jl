using Test
using DrWatson

println("JULIA-TRIGGER-START")

@testset "JULIA-336 explicit digits overrides sigdigits" begin
    data = (a = 1.23456,)
    @test savename(data; digits = 2, sigdigits = 4) == "a=1.23"
end
