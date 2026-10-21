using Test
using DataStructures

println("JULIA-TRIGGER-START")

@testset "JULIA-706 failed conversion leaves CircularBuffer unchanged" begin
    buffer = CircularBuffer{Int}(5)
    @test size(buffer) == (0,)
    failure = try
        push!(buffer, 1.5)
        nothing
    catch exception
        exception
    end
    @test failure isa Exception
    @test size(buffer) == (0,)
    push!(buffer, 1)
    @test collect(buffer) == [1]
end
