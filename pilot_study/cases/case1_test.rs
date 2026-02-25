#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_value() {
        let result = get_value();
        assert_eq!(result, 42);
    }
}
