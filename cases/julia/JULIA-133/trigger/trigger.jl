using Test
using JuMP: Containers

println("JULIA-TRIGGER-START")
@testset "Issue 4213 tuple keys" begin
    keys = [(:a, :b)]
    array = Containers.DenseAxisArray([:answer], keys)
    @test array[(:a, :b)] == :answer
    @test_throws KeyError array[:a, :b]
end
