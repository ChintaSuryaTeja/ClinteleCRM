import type { Metadata } from "next";

import { Table, Td, Th } from "@/components/table";
import { EmptyState, PageTitle, Panel, SectionTitle } from "@/components/ui";
import { formatDateTime, formatNumber } from "@/lib/format";
import { getCurrentUser, getImports } from "@/lib/server-api";
import type { ImportJob } from "@/lib/types";

import { AutoRefresh } from "./AutoRefresh";
import { DeleteImportButton } from "./DeleteImportButton";
import { ManualOrderForm } from "./ManualOrderForm";
import { UploadForm } from "./UploadForm";

export const metadata: Metadata = { title: "Import" };

const COLUMNS = [
  { name: "order_id", required: true, about: "Your order or invoice number" },
  { name: "order_date", required: true, about: "Like 2024-03-31 or 2024-03-31 14:05" },
  { name: "customer_id", required: true, about: "Your ID for the customer" },
  { name: "product_code", required: true, about: "Your SKU or product code" },
  { name: "quantity", required: true, about: "A whole number above zero" },
  { name: "unit_price", required: true, about: "Price of one item, without the currency sign" },
  { name: "customer_name", required: false, about: "" },
  { name: "customer_email", required: false, about: "" },
  { name: "product_name", required: false, about: "" },
];

const STATUS_LABELS: Record<ImportJob["status"], string> = {
  queued: "Waiting to start",
  running: "Importing…",
  succeeded: "Done",
  failed: "Failed",
  deleting: "Deleting…",
};

const BUSY: ImportJob["status"][] = ["queued", "running", "deleting"];

export default async function ImportPage() {
  const user = await getCurrentUser();
  if (user.role !== "admin") {
    return (
      <div className="mx-auto max-w-6xl">
        <PageTitle>Import</PageTitle>
        <div className="mt-8">
          <EmptyState title="Only admins can import data">
            <p>Ask an admin at {user.organization.name} to upload new sales data.</p>
          </EmptyState>
        </div>
      </div>
    );
  }

  const jobs = await getImports();
  const inProgress = jobs.some((job) => BUSY.includes(job.status));

  return (
    <div className="mx-auto max-w-6xl">
      <AutoRefresh active={inProgress} />
      <PageTitle>Import</PageTitle>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Panel className="p-5 sm:p-6">
          <SectionTitle>Upload orders</SectionTitle>
          <p className="mt-1 mb-5 text-sm text-muted">
            One row per product in an order. Orders you have imported before are skipped, so
            uploading the same file twice is safe.
          </p>
          <UploadForm />
        </Panel>

        <Panel className="p-5 sm:p-6">
          <SectionTitle>Columns the file needs</SectionTitle>
          <p className="mt-1 text-sm text-muted">
            Column names can be in any order and any case.{" "}
            <a
              href="/import-template.csv"
              download
              className="font-medium text-accent underline underline-offset-2"
            >
              Download a template
            </a>
          </p>
          <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sm">
            {COLUMNS.map((column) => (
              <div key={column.name} className="contents">
                <dt className="font-medium">{column.name}</dt>
                <dd className="text-muted">{column.required ? column.about : "Optional"}</dd>
              </div>
            ))}
          </dl>
        </Panel>
      </div>

      <Panel className="mt-6 p-5 sm:p-6">
        <SectionTitle>Add an order by hand</SectionTitle>
        <p className="mt-1 mb-5 text-sm text-muted">
          For a single order without making a file. It&apos;s checked and saved like an upload and
          listed under Past imports, where you can delete it.
        </p>
        <ManualOrderForm />
      </Panel>

      <Panel className="mt-6 p-5 sm:p-6">
        <SectionTitle>Past imports</SectionTitle>
        {jobs.length === 0 ? (
          <p className="mt-3 text-sm text-muted">
            No imports yet. Each upload and its result will be listed here.
          </p>
        ) : (
          <div className="mt-4">
            <Table label="Past imports">
              <thead>
                <tr>
                  <Th>File</Th>
                  <Th>Uploaded</Th>
                  <Th>Status</Th>
                  <Th numeric>Imported</Th>
                  <Th numeric>Rejected</Th>
                  <Th numeric>Already imported</Th>
                  <Th>
                    <span className="sr-only">Error report</span>
                  </Th>
                  <Th>
                    <span className="sr-only">Delete</span>
                  </Th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <ImportRow key={job.id} job={job} />
                ))}
              </tbody>
            </Table>
          </div>
        )}
      </Panel>
    </div>
  );
}

function ImportRow({ job }: { job: ImportJob }) {
  const finished = job.status === "succeeded" || job.status === "failed";
  const hasReport = job.status === "failed" || job.rows_rejected > 0;
  return (
    <tr>
      <Td>
        <span className="font-medium [overflow-wrap:anywhere]">{job.filename}</span>
        {job.failure_reason && (
          <span className="mt-0.5 block text-danger">{job.failure_reason}</span>
        )}
      </Td>
      <Td className="whitespace-nowrap">{formatDateTime(job.created_at)}</Td>
      <Td className={`whitespace-nowrap ${job.status === "failed" ? "text-danger" : ""}`}>
        {STATUS_LABELS[job.status]}
      </Td>
      <Td numeric>{finished ? formatNumber(job.rows_imported) : "–"}</Td>
      <Td numeric>{finished ? formatNumber(job.rows_rejected) : "–"}</Td>
      <Td numeric>{finished ? formatNumber(job.rows_skipped) : "–"}</Td>
      <Td className="whitespace-nowrap">
        {hasReport && (
          <a
            href={`/api/imports/${job.id}/errors.csv`}
            download
            className="font-medium text-accent underline underline-offset-2"
          >
            Error report
          </a>
        )}
      </Td>
      <Td className="whitespace-nowrap">
        {finished && (
          <DeleteImportButton
            jobId={job.id}
            rowsImported={job.rows_imported}
            failed={job.status === "failed"}
          />
        )}
      </Td>
    </tr>
  );
}
