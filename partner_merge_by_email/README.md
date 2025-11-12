# Partner Merge by Email

## Description

This module allows you to merge all duplicate partners that share the same email address automatically without asking one by one. It provides a wizard to execute the merge operation in batch mode.

## Features

- **Find Duplicate Partners**: Search for all partners with duplicate email addresses
- **Preview Before Merge**: Review the list of duplicates before merging
- **Automatic Merge**: Merge all duplicates in one action
- **Master Selection**: The oldest partner (by creation date) is kept as the master
- **Data Transfer**: All related records (sales orders, invoices, etc.) are transferred to the master partner

## Usage

1. Go to Contacts > Merge Duplicate Partners
2. Click "Find Duplicates" to search for partners with duplicate emails
3. Review the preview list showing all duplicate groups
4. Click "Merge All" to merge all duplicates automatically

## Technical Details

The module:
- Groups partners by email address (case-insensitive)
- Selects the oldest partner as the master
- Transfers all related records from duplicates to master
- Transfers child contacts to master
- Merges partner categories
- Deactivates duplicate partners after merge

## Author

**Xtendoo**
- Website: http://www.xtendoo.es

## License

AGPL-3

## Version

18.0.1.0.0

