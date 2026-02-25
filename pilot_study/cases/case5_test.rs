#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_push_and_read() {
        let result = push_and_read();
        assert_eq!(result, 1);
    }
}
