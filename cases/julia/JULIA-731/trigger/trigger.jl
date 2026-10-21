using Test

println("JULIA-TRIGGER-START")

module TestEmptyDocString
using Test
using Comonicon

@cast test() = @test true

"""
"""
@main
end

@testset "empty docstring command" begin
    TestEmptyDocString.command_main(["test"])
end

println("JULIA-731 trigger completed")
