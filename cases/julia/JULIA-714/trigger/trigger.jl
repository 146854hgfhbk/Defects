println("JULIA-TRIGGER-START")
using Test
using AbstractAlgebra

@testset "JULIA-714 BigInt zero mutation" begin
    value = BigInt(42)
    result = zero!(value)
    @test value == 42
    @test result == 0
end
