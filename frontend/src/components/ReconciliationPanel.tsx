"use client";

import React from "react";
import {
  CheckCircle2,
  AlertTriangle,
  Clock,
  ShieldAlert,
  DollarSign,
  Package,
  Calculator,
  XCircle,
} from "lucide-react";
import { ReconciliationDetail } from "@/lib/types";

interface Props {
  reconciliation?: ReconciliationDetail | null;
  status: "PENDING" | "RECONCILED" | "DISCREPANCY_FOUND";
}

export default function ReconciliationPanel({ reconciliation, status }: Props) {
  const isReconciled = status === "RECONCILED";
  const hasDiscrepancy = status === "DISCREPANCY_FOUND";

  const pillars = [
    {
      key: "math",
      title: "Cálculo Factura",
      valid: Boolean(reconciliation?.math_valid),
      icon: Calculator,
      okDesc: "Subtotal + IGV = Total",
      failDesc: "Descuadre en importes",
    },
    {
      key: "goods",
      title: "Recepción Almacén",
      valid: Boolean(reconciliation?.goods_matched),
      icon: Package,
      okDesc: "Coincide con Guía",
      failDesc: "Diferencia de unidades",
    },
    {
      key: "payment",
      title: "Pago Bancario",
      valid: Boolean(reconciliation?.payment_matched),
      icon: DollarSign,
      okDesc: "Cubierto al 100%",
      failDesc: "Saldo pendiente",
    },
  ];

  return (
    <section className="surface-card p-5 space-y-4" aria-labelledby="reconcile-heading">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 id="reconcile-heading" className="text-sm font-semibold text-zinc-100">
            Resultado de Conciliación
          </h2>
          <p className="text-xs text-zinc-400">
            Factura vs. Guía de Remisión vs. Voucher
          </p>
        </div>

        <div>
          {isReconciled && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 text-xs font-semibold">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" aria-hidden="true" />
              <span>Conciliado</span>
            </span>
          )}
          {hasDiscrepancy && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-500/10 border border-rose-500/25 text-rose-300 text-xs font-semibold">
              <AlertTriangle className="h-3.5 w-3.5 text-rose-400" aria-hidden="true" />
              <span>Con Discrepancias</span>
            </span>
          )}
          {!isReconciled && !hasDiscrepancy && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-500/10 border border-amber-500/25 text-amber-300 text-xs font-semibold">
              <Clock className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />
              <span>Pendiente</span>
            </span>
          )}
        </div>
      </div>

      {/* Summary Banner */}
      {reconciliation?.summary && (
        <div
          className={`p-3.5 rounded-lg border text-xs leading-relaxed ${
            isReconciled
              ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-200"
              : hasDiscrepancy
              ? "bg-rose-500/5 border-rose-500/20 text-rose-200"
              : "bg-amber-500/5 border-amber-500/20 text-amber-200"
          }`}
        >
          {reconciliation.summary}
        </div>
      )}

      {/* 3 Pillars */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
        {pillars.map((pillar) => {
          const IconComponent = pillar.icon;
          return (
            <div
              key={pillar.key}
              className="p-3 rounded-lg bg-[#0b0b0d] border border-zinc-800/90 flex flex-col justify-between gap-2"
            >
              <div className="flex items-center justify-between">
                <IconComponent
                  className={`h-4 w-4 ${pillar.valid ? "text-emerald-400" : "text-rose-400"}`}
                  aria-hidden="true"
                />
                {pillar.valid ? (
                  <span className="inline-flex items-center gap-1 text-[0.65rem] font-mono font-semibold text-emerald-400">
                    <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                    OK
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[0.65rem] font-mono font-semibold text-rose-400">
                    <XCircle className="h-3 w-3" aria-hidden="true" />
                    OBS
                  </span>
                )}
              </div>
              <div>
                <p className="text-xs font-semibold text-zinc-200">{pillar.title}</p>
                <p className="text-[0.68rem] text-zinc-400 mt-0.5">
                  {pillar.valid ? pillar.okDesc : pillar.failDesc}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Discrepancies */}
      {reconciliation?.discrepancies && reconciliation.discrepancies.length > 0 && (
        <div className="space-y-2.5 pt-1">
          <h3 className="text-xs font-semibold text-rose-400 flex items-center gap-1.5">
            <ShieldAlert className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Observaciones detectadas ({reconciliation.discrepancies.length})</span>
          </h3>

          <ul className="space-y-2">
            {reconciliation.discrepancies.map((disc, idx) => (
              <li
                key={idx}
                className="p-3 bg-rose-500/5 border border-rose-500/20 rounded-lg text-xs flex flex-wrap items-start justify-between gap-2"
              >
                <div className="space-y-1">
                  <span className="inline-block font-mono text-[0.68rem] font-semibold text-rose-300 bg-rose-950/50 px-1.5 py-0.5 rounded">
                    {disc.type}
                  </span>
                  {disc.item_description && (
                    <p className="text-zinc-200">
                      Ítem: <strong>{disc.item_description}</strong> — Facturado:{" "}
                      <span className="font-mono">{disc.billed_quantity}</span> | Recibido:{" "}
                      <span className="font-mono font-semibold text-rose-300">{disc.received_quantity}</span>
                    </p>
                  )}
                  {disc.balance_pending !== undefined && (
                    <p className="text-zinc-200">
                      Facturado: <span className="font-mono">S/ {Number(disc.billed_total).toFixed(2)}</span> | Pagado:{" "}
                      <span className="font-mono">S/ {Number(disc.paid_total).toFixed(2)}</span> —{" "}
                      <strong className="text-rose-300 font-mono">
                        Pendiente: S/ {Number(disc.balance_pending).toFixed(2)}
                      </strong>
                    </p>
                  )}
                  {disc.expected !== undefined && disc.declared !== undefined && (
                    <p className="text-zinc-200">
                      Esperado: <span className="font-mono">S/ {Number(disc.expected).toFixed(2)}</span> vs.
                      Declarado: <span className="font-mono text-rose-300">S/ {Number(disc.declared).toFixed(2)}</span>
                    </p>
                  )}
                  {disc.invoice_currency && (
                    <p className="text-zinc-200">
                      Moneda Factura: <strong>{disc.invoice_currency}</strong> vs. Voucher:{" "}
                      <strong>{disc.voucher_currency}</strong>
                    </p>
                  )}
                </div>

                {disc.shortage && (
                  <span className="px-2 py-0.5 rounded bg-rose-500/15 text-rose-200 font-mono font-semibold">
                    -{disc.shortage} und.
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
