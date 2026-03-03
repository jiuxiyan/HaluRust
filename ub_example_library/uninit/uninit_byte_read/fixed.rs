fn main() {
    // Initialize the vector with 10 zeros
    let v: Vec<u8> = vec![0u8; 10];
    
    // Access the element safely using indexing
    let val = v[5];
    let x = val + 1;
    
    println!("Value of x: {}", x);
}