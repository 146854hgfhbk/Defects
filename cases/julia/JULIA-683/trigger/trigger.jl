using Test
using IntervalArithmetic

println("JULIA-TRIGGER-START")

@testset "JULIA-683 mixed interval muladd regression" begin
    expected = interval(1.1) * interval(2) + interval(3)
    @test muladd(interval(1.1), interval(2), 3) ≛ expected
    @test muladd(interval(1.1), 2, interval(3)) ≛ expected
    @test muladd(1.1, interval(2), interval(3)) ≛ expected
end
