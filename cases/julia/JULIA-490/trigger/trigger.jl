println("JULIA-TRIGGER-START")
using Test

if get(ENV, "JULIA_490_CHILD", "0") == "1"
    error("child mode must be executed through the generated child command")
else
    @testset "JULIA-490 concurrent generated functions" begin
        child = """
            using RuntimeGeneratedFunctions
            RuntimeGeneratedFunctions.init(Main)
            tasks = map(1:max(4, Threads.nthreads())) do k
                Threads.@spawn begin
                    for i in 1:100
                        function_value = @RuntimeGeneratedFunction(
                            Base.remove_linenums!(:((x, y) -> x + y + \$i * \$k))
                        )
                        function_value(1, 2) == 3 + i * k || error(\"wrong result\")
                    end
                end
            end
            foreach(fetch, tasks)
        """
        # Use the OS timeout utility: a synchronous Julia wait does not
        # reliably service Julia Timer callbacks while the child is stuck.
        command = `timeout --signal=KILL 60s $(Base.julia_cmd()) --startup-file=no --project=$(Base.active_project()) --threads=8 -e $child`
        process = run(addenv(command, "JULIA_490_CHILD" => "1"); wait=false)
        wait(process)
        @test success(process)
    end
end
