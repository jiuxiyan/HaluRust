fn foo(x: &mut (i32, i32)) -> &mut i32 {
    // If we need to read the tuple's current state, we must do it before 
    // creating a mutable borrow of its field that we intend to return.
    let _val = *x; 
    
    // Return a mutable reference to the second element using safe field projection.
    // The Rust borrow checker ensures that 'x' cannot be accessed in a way that 
    // conflicts with 'ret' as long as 'ret' is alive.
    &mut x.1
}

fn main() {
    let arg = &mut (1, 2);
    let ret = foo(arg);
    *ret = 3;
}