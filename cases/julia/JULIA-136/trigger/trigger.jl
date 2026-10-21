using Test
using SciMLBase

println("JULIA-TRIGGER-START")
@testset "controller kwargs are rejected" begin
    @test_throws SciMLBase.CommonKwargError SciMLBase.checkkwargs(
        SciMLBase.KeywordArgError; gamma=0.9
    )
    err = try
        SciMLBase.checkkwargs(SciMLBase.KeywordArgError; gamma=0.9)
        nothing
    catch exception
        exception
    end
    @test err isa SciMLBase.CommonKwargError
    message = sprint(showerror, err)
    @test occursin("controller", message)
    @test occursin("PIController", message)
    @test occursin("gamma", message)
end
