using Test
using SciMLBase
using SymbolicIndexingInterface

println("JULIA-TRIGGER-START")
@testset "save_idxs rejects observed quantities" begin
    cache = SymbolCache([:x, :y], [:p], :t)
    parameters = [0.5]
    observed = :(x + y)
    @test is_observed(cache, observed)
    @test !is_variable(cache, observed)

    err = try
        SciMLBase.SavedSubsystem(cache, parameters, [observed])
        nothing
    catch exception
        exception
    end
    @test err isa ArgumentError
    message = sprint(showerror, err)
    @test occursin("observed", message)
    @test occursin("1036", message)
    @test occursin("SavingCallback", message)

    saved = SciMLBase.SavedSubsystem(cache, parameters, [:x])
    @test SciMLBase.get_saved_state_idxs(saved) == [1]
end
