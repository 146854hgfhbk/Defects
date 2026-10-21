println("JULIA-TRIGGER-START")
using Test
import MathOptInterface as MOI
import MathOptInterface.FileFormats: NL

@testset "JULIA-054 NL defined variables" begin
    model = NL._CacheModel()
    io = IOBuffer("V2 0 0\nn0\n")
    NL._parse_section(io, model)
    @test length(model.defined_variables) == 1
    @test model.defined_variables[2] === 0.0

    model = NL._CacheModel()
    NL._resize_variables(model, 2)
    io = IOBuffer("V1 0 0\nv0\n")
    NL._parse_section(io, model)
    @test length(model.defined_variables) == 1
    @test model.defined_variables[1] === MOI.VariableIndex(1)
end
println("JULIA-054 trigger completed")
