fn main() {
    // Initialize x safely. 
    // If the intent was to crash, use panic!() or handle an Option/Result.
    let x: i32 = 0; 
    
    // This will now print instead of triggering UB.
    println!("Value of x: {}", x);
}