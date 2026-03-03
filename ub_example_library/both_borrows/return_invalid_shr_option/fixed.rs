// Make sure that we cannot return a `&` that got already invalidated, not even in an `Option`.
fn foo(x: &mut (i32, i32)) -> Option<&i32> {
    // Perform the update first while we have exclusive access.
    *x = (42, 23);
    // Create the shared reference after the update is complete.
    Some(&x.1)
}

fn main() {
    match foo(&mut (1, 2)) {
        Some(_x) => {}
        None => {}
    }
}