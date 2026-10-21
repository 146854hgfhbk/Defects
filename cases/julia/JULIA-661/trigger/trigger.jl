# JULIA-661 trigger: studentized-range boundary behaviour.
# Assertions are copied verbatim from the upstream fixed testset.
using StatsFuns
using Test
println("JULIA-TRIGGER-START")

@testset "JULIA-661 srdist boundary behaviour" begin
    @test iszero(srdistcdf(2.0, 2.0, 0.0))
    @test isone(srdistccdf(2.0, 2.0, 0.0))
    @test srdistlogcdf(2.0, 2.0, 0.0) == -Inf
    @test iszero(srdistlogccdf(2.0, 2.0, 0.0))
    @test isone(srdistcdf(2.0, 2.0, Inf))
    @test iszero(srdistccdf(2.0, 2.0, Inf))
    @test iszero(srdistlogcdf(2.0, 2.0, Inf))
    @test srdistlogccdf(2.0, 2.0, Inf) == -Inf
end

println("JULIA-661 trigger completed")
