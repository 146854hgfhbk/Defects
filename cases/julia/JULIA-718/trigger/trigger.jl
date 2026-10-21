using OhMyThreads

# Regression MWE from the `@only_one` test added by upstream PR #100.
# With `ntasks = 2`, one task must enter the region in each of five batches.
x = Ref(0)
@tasks for _ in 1:10
    @set ntasks = 2
    @only_one begin
        x[] += 1
    end
end

@assert x[] == 5
