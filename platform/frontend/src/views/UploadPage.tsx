import { useState, type ChangeEvent } from "react";
import { Link } from "react-router-dom";
import { uploadBundle, type UploadResult } from "../api/client";
import { ErrorMessage } from "../components/UI";

/** Check if an error message indicates a duplicate bundle (409). */
function isDuplicateError(msg: string): boolean {
  return msg.includes("409") || msg.toLowerCase().includes("already uploaded");
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [repoName, setRepoName] = useState("");
  const [token, setToken] = useState("");
  const [progress, setProgress] = useState<number | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    setFile(e.target.files?.[0] ?? null);
    setResult(null);
    setError("");
  }

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError("");
    setResult(null);
    setProgress(0);

    try {
      const res = await uploadBundle(file, repoName, token, setProgress);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
      setProgress(null);
    }
  }

  function resetForm() {
    setFile(null);
    setRepoName("");
    setResult(null);
    setError("");
    setProgress(null);
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-6">Upload Artifact Bundle</h2>

      <div className="bg-card rounded-lg border border-gray-200 p-6 max-w-xl">
        {/* Warning */}
        <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded text-sm mb-5">
          <strong>⚠ Source-derived data:</strong> Uploaded .ai-debt artifacts may contain
          source-derived evidence snippets, file paths, hashes, and analysis metadata.
          Review bundle contents before uploading to shared platforms.
        </div>

        {/* File input */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Bundle file (.tar.gz)
          </label>
          <input
            type="file"
            accept=".tar.gz,.tgz"
            onChange={handleFileChange}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-primary file:text-white hover:file:bg-primary-dark"
          />
          {file && (
            <p className="text-xs text-muted mt-1">
              {(file.size / 1024).toFixed(1)} KB
            </p>
          )}
        </div>

        {/* Repository name */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Repository name <span className="text-muted">(optional — uses project-profile.json if empty)</span>
          </label>
          <input
            type="text"
            value={repoName}
            onChange={(e) => setRepoName(e.target.value)}
            placeholder="my-repo"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          />
        </div>

        {/* Token */}
        <div className="mb-5">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Admin token
          </label>
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Enter admin token"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          />
        </div>

        {/* Upload button */}
        <button
          onClick={handleUpload}
          disabled={!file || !token || uploading}
          className="w-full px-4 py-2 bg-primary text-white text-sm rounded hover:bg-primary-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {uploading ? `Uploading… ${progress ?? 0}%` : "Upload Bundle"}
        </button>

        {/* Progress bar */}
        {progress !== null && (
          <div className="mt-3 bg-gray-200 rounded-full h-2">
            <div
              className="bg-primary rounded-full h-2 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}

        {/* Error — duplicate */}
        {error && isDuplicateError(error) && (
          <div className="mt-4 bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded text-sm">
            <strong>⚠ Duplicate bundle:</strong> This artifact bundle has already been uploaded.
            Each unique bundle can only be uploaded once.
            <div className="mt-2">
              <Link
                to="/"
                className="text-primary hover:underline text-sm"
              >
                → View repositories
              </Link>
            </div>
          </div>
        )}

        {/* Error — general */}
        {error && !isDuplicateError(error) && <ErrorMessage message={error} />}

        {/* Result */}
        {result && (
          <div className="mt-4 bg-green-50 border border-green-200 rounded p-4">
            <p className="text-sm font-semibold text-green-800 mb-2">
              ✅ Upload successful
            </p>
            <dl className="text-sm space-y-1">
              <div className="flex gap-2">
                <dt className="text-muted">Bundle ID:</dt>
                <dd className="font-mono text-xs">{result.bundle_id}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="text-muted">Repository:</dt>
                <dd className="font-mono text-xs">{result.repository_id}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="text-muted">Valid:</dt>
                <dd>{result.is_valid ? "Yes" : "No"}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="text-muted">Findings:</dt>
                <dd>{result.findings_count}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="text-muted">Content hash:</dt>
                <dd className="font-mono text-xs">{result.content_hash.slice(0, 16)}…</dd>
              </div>
            </dl>

            {result.parse_errors.length > 0 && (
              <div className="mt-2 text-sm text-yellow-700">
                <strong>Parse warnings:</strong>
                <ul className="list-disc ml-4">
                  {result.parse_errors.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-3 pt-3 border-t border-green-200 flex items-center gap-4">
              <Link
                to="/"
                className="text-primary hover:underline text-sm font-medium"
              >
                → View repositories
              </Link>
              <button
                onClick={resetForm}
                className="text-muted hover:text-gray-700 text-sm"
              >
                Upload another
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
