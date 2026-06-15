import { useRef, useState } from "react";

export function UploadPanel({
  token,
}: {
  token: string | null;
}) {
  const [files, setFiles] = useState<File[]>([]);
  const [status, setStatus] = useState("");
  const [uploading, setUploading] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (
    selectedFiles: FileList | null
  ) => {
    if (!selectedFiles) return;

    setFiles(Array.from(selectedFiles));
  };

  const handleUpload = async () => {
    if (!files.length) {
      setStatus("Please select files");
      return;
    }

    if (!token) {
      setStatus("Please login first");
      return;
    }

    try {
      setUploading(true);
      setStatus("");

      for (const file of files) {
        const formData = new FormData();

        formData.append("file", file);

        const response = await fetch(
          "/api/v1/documents/upload",
          {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
            },
            body: formData,
          }
        );

        if (!response.ok) {
          throw new Error(await response.text());
        }
      }

      setStatus(
        `✅ ${files.length} file(s) uploaded successfully`
      );

      setFiles([]);
    } catch (error) {
      console.error(error);

      setStatus("❌ Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-panel">
      <div className="upload-header">
        <h3>Upload Documents</h3>

        <span className="upload-supported">
          PDF • DOCX • TXT • MD
        </span>
      </div>

      <div
        className="upload-dropzone"
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          onChange={(e) =>
            handleFiles(e.target.files)
          }
        />

        <div className="upload-icon">
          📄
        </div>

        <p>
          Drag & drop files here or click
          to browse
        </p>
      </div>

      {files.length > 0 && (
        <div className="upload-files">
          {files.map((file) => (
            <div
              key={file.name}
              className="upload-file"
            >
              <span>{file.name}</span>

              <small>
                {(
                  file.size /
                  1024 /
                  1024
                ).toFixed(2)}
                MB
              </small>
            </div>
          ))}
        </div>
      )}

      <button
        className="primary-button"
        disabled={
          uploading || files.length === 0
        }
        onClick={handleUpload}
      >
        {uploading
          ? "Uploading..."
          : "Upload Files"}
      </button>

      {status && (
        <div className="upload-status">
          {status}
        </div>
      )}
    </div>
  );
}
