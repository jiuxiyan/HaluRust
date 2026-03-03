fn main() {
    let numerator: i32 = 2;
    let divisor: i32 = 0;

    match numerator.checked_div(divisor) {
        Some(result) => println!("Result: {}", result),
        None => println!("Error: Division by zero or overflow"),
    }
}