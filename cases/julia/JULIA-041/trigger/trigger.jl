using Test
import MathOptInterface as MOI

println("JULIA-TRIGGER-START")
@testset "LP negative upper bound retains default lower bound" begin
    model = MOI.FileFormats.LP.Model()
    input = IOBuffer("Minimize\nobj: x\nBounds\nx <= -1\nEnd")
    read!(input, model)
    output = IOBuffer()
    write(output, model)
    seekstart(output)
    text = read(output, String)
    @test occursin("Bounds\n0 <= x <= -1\nEnd", text)
end
