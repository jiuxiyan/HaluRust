#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_increment_through_alias() {
        let mut val = 10;
        let result = increment_through_alias(&mut val);
        assert_eq!(result, 11);
    }
}
