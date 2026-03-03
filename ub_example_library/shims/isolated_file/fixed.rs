use std::fs::File;
use std::io;
use std::fs;

fn main() -> io::Result<()> {
    // Ensure the file exists so that the subsequent open call succeeds.
    fs::write("file.txt", "Hello, world!")?;

    // Using '?' instead of 'unwrap()' prevents the panic and 
    // returns the error gracefully if the file is missing.
    let _file = File::open("file.txt")?;
    
    Ok(())
}