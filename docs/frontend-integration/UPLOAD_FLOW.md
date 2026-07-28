# Upload Flow

1. Create an upload session with filename, declared MIME type, declared size, asset type, and optional product ID.
2. Upload binary media directly to the returned presigned URL.
3. Call complete-upload.
4. Poll processing jobs after enqueueing processing.
