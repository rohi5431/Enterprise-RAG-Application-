import { useState } from "react";

export function UploadPanel({ token }: { token: string | null }){
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState("");

  const handleUpload = async () => {
    if (!file) return alert("Please select a file");
    if (!token) return alert("Please sign in first");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/v1/documents/upload", {
        method: "POST",
        body: formData,
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      if (!res.ok) throw new Error(await res.text());
      setStatus("File uploaded successfully ✅");
      setFile(null);
    } catch (err) {
      console.error("UPLOAD ERROR:", err);
      setStatus("Upload failed ❌");
    }
  };

  return (
    <div className="upload-panel">
      <h2>Upload Documents</h2>
      <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} />
      <button onClick={handleUpload} disabled={!file}>
        Upload
      </button>
      {status && <p>{status}</p>}
    </div>
  );
}
