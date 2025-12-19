# 🧹 Duplicate Management

This document explains how to manage duplicate sources in the Project Infinit database to maintain data quality and prevent skewed analytics.

## 🎯 Why Duplicate Detection Matters

- **Accurate Analytics**: Duplicates can inflate metrics and skew trend analysis
- **Storage Efficiency**: Saves disk space and improves query performance
- **Data Quality**: Ensures reliable reporting and visualization
- **Cost Optimization**: Reduces processing overhead in ETL pipelines

## 🔍 How Duplicate Detection Works

### **Content Hashing**

- Each source gets a SHA-256 hash of its normalized content
- Normalization removes extra whitespace and converts to lowercase
- Allows detection of semantically identical content from different URLs

### **Duplicate Criteria**

1. **Exact URL Match**: Same URL = duplicate
2. **Content Hash Match**: Same normalized content = duplicate
3. **Title Similarity**: Basic fuzzy matching (future enhancement)

### **Retention Policy**

- When duplicates are found, the **most recent** source is kept
- Older duplicates are removed
- All associated analytical data is preserved

## 🛠️ Available Tools

### **1. Update Content Hashes**

Calculate and store content hashes for sources that don't have them yet:

```bash
python database/deduplicate_sources.py update-hashes
```

Options:

- `--batch-size N`: Process in batches of N sources (default: 1000)

### **2. Find Duplicates (Dry Run)**

Scan for duplicates without removing them:

```bash
python database/deduplicate_sources.py find
```

Shows how many duplicates would be removed.

### **3. Remove Duplicates**

Actually remove duplicate sources from database:

```bash
python database/deduplicate_sources.py remove
```

**⚠️ Warning**: This operation cannot be undone! Use `--force` to skip confirmation.

### **4. Show Statistics**

Get overview of duplicate status in database:

```bash
python database/deduplicate_sources.py stats
```

Shows:

- Total sources with/without hashes
- Number of unique content hashes
- Duplicate groups and counts

## 💻 Programmatic Usage

### **Safe Source Insertion**

Use the database connector's safe insertion methods:

```python
from database.db_loader import DBConnector

db = DBConnector()

# Insert single source with duplicate checking
source = db.insert_source_safe(
    movement_id=1,
    url="https://example.com/article",
    content_full="Article content...",
    source_name="Example Article"
)

# Bulk insert with duplicate detection
sources_data = [
    {
        'movement_id': 1,
        'url': 'https://example.com/1',
        'content_full': 'Content 1...',
        'source_name': 'Article 1'
    },
    # ... more sources
]

stats = db.bulk_insert_sources_safe(sources_data)
print(f"Inserted: {stats['inserted']}, Duplicates skipped: {stats['duplicates_skipped']}")
```

### **Manual Duplicate Management**

```python
# Find duplicates for specific content
duplicates = db.find_duplicates(content_hash="some_hash_value")

# Or find by URL
duplicates = db.find_duplicates(url="https://example.com/article")

# Remove all duplicates (dry run first!)
stats = db.remove_duplicates(dry_run=True)
if stats['duplicates_found'] > 0:
    db.remove_duplicates(dry_run=False)
```

## 📊 Integration with ETL Pipeline

### **Automatic Deduplication in Spiders**

Update your spiders to use safe insertion:

```python
# In your spider's parse method
from database.db_loader import DBConnector

db = DBConnector()

# Instead of direct Source creation
source = db.insert_source_safe(
    movement_id=movement.id,
    url=response.url,
    content_full=extracted_text,
    source_name=title,
    domain=domain,
    publication_date=pub_date,
    # ... other fields
)
```

### **Batch Processing**

For large data imports, use bulk insertion:

```python
# Collect all sources first
all_sources = []

# ... collect data from scraping ...

# Then bulk insert with deduplication
stats = db.bulk_insert_sources_safe(all_sources, check_duplicates=True)
```

## 🔧 Configuration Options

### **Disable Duplicate Checking**

For performance-critical operations:

```python
# Skip duplicate checks (not recommended for production)
source = db.insert_source_safe(..., check_duplicates=False)
stats = db.bulk_insert_sources_safe(sources, check_duplicates=False)
```

### **Custom Hash Calculation**

Override the default hashing logic:

```python
# Custom normalization
def custom_hash(text):
    # Your custom normalization logic
    normalized = text.lower().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()

# Use in your code
content_hash = custom_hash(content)
```

## 📈 Monitoring & Maintenance

### **Regular Cleanup Schedule**

Set up cron jobs for regular maintenance:

```bash
# Daily: Update hashes for new sources
0 2 * * * cd /path/to/project && python database/deduplicate_sources.py update-hashes

# Weekly: Remove duplicates
0 3 * * 0 cd /path/to/project && python database/deduplicate_sources.py remove --force

# Monthly: Check statistics
0 4 1 * * cd /path/to/project && python database/deduplicate_sources.py stats >> logs/dedup_stats.log
```

### **Performance Monitoring**

Track deduplication performance:

```python
import time

start_time = time.time()
stats = db.remove_duplicates(dry_run=False)
duration = time.time() - start_time

print(f"Deduplication took {duration:.2f}s for {stats['scanned']} sources")
```

## 🚨 Best Practices

### **1. Always Test First**

```bash
# Always run dry-run first
python database/deduplicate_sources.py find
# Review results before actual removal
python database/deduplicate_sources.py remove
```

### **2. Backup Before Major Operations**

```bash
# Create backup before removing duplicates
pg_dump mydatabase > backup_before_dedup.sql  # PostgreSQL
# or
sqlite3 data.db .backup backup.db             # SQLite
```

### **3. Monitor Impact on Analytics**

After deduplication, check that your analytical queries still work correctly:

```sql
-- Verify analytics views still work
SELECT * FROM movement_analytics LIMIT 5;
SELECT COUNT(*) FROM monthly_trends;
```

### **4. Handle Edge Cases**

- **Near-duplicates**: Content that's 95% similar but not identical
- **Language variants**: Same content in different languages
- **Paywall content**: Partial content that looks like duplicates
- **Time-sensitive content**: Breaking news that gets updated

## 🔍 Troubleshooting

### **"No module named 'database'"**

```bash
cd /home/adam/Dokumenty/projects/project_infinit
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### **Hash calculation errors**

- Check that content is properly decoded UTF-8
- Handle None/empty content gracefully
- Log problematic sources for manual review

### **Performance issues with large datasets**

- Use batch processing
- Process during off-peak hours
- Consider database indexing on content_hash
- Use database-specific optimizations (e.g., PostgreSQL GIN indexes)

### **False positives in duplicate detection**

- Review hash calculation logic
- Consider additional similarity metrics
- Implement manual override mechanisms
- Add confidence scores to duplicate detection

## 📋 Future Enhancements

- **Fuzzy matching**: Detect near-duplicate content
- **Image duplicate detection**: For multimedia content
- **Cross-language duplicate detection**: Same content in different languages
- **Machine learning-based deduplication**: AI-powered similarity detection
- **Real-time deduplication**: Check during scraping
- **Duplicate clusters**: Group related but not identical content
