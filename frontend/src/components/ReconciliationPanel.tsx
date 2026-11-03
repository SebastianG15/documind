"use client";

import React from "react";
import { CheckCircle2, AlertTriangle, Clock, ShieldAlert, ArrowRight, DollarSign, Package, Calculator } from "lucide-react";
import { ReconciliationDetail } from "@/lib/types";

interface Props {
  reconciliation?: ReconciliationDetail | null;
  status: "PENDING" | "RECONCILED" | "DISCREPANCY_FOUND";
}

export default function ReconciliationPanel({ reconciliation, status }: Props) {
  const isReconciled = status === "RECONCILED";
  const hasDiscrepancy = status === "DISCREPANCY_FOUND";

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-2xl p-6 shadow-xl space-y-6">
      {/* Header with status badge */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-white tracking-tight">Resultado de Cotejo de 3 Vías</h3>
          <p className="text-xs text-gray-400 mt-0.5">Auditoría cruzada Factura vs. Guía de Remisión vs. Voucher Bancario</p>
        </div>

        <div>
          {isReconciled && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold tracking-wide">
              <CheckCircle2 className="h-4 w-4" />
              100% CONCILIADO
            </span>
          )}
          {hasDiscrepancy && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-bold tracking-wide animate-pulse">
              <AlertTriangle className="h-4 w-4" />
              DISCREPANCIA DETECTADA
            </span>
          )}
          {!isReconciled && !hasDiscrepancy && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-bold tracking-wide">
              <Clock className="h-4 w-4" />
              PENDIENTE DE DOCUMENTOS
            </span>
          )}
        </div>
      </div>

      {/* Summary message */}
      {reconciliation?.summary && (
        <div
          className={`p-4 rounded-xl border text-sm leading-relaxed ${
            isReconciled
              ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-300"
              : hasDiscrepancy
              ? "bg-rose-500/5 border-rose-500/20 text-rose-300"
              : "bg-amber-500/5 border-amber-500/20 text-amber-300"
          }`}
        >
          {reconciliation.summary}
        </div>
      )}

      {/* 3 Verification Pillars */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Pillar 1: Math */}
        <div className="p-4 rounded-xl bg-[#1e293b]/40 border border-gray-800 flex items-start gap-3">
          <div
            className={`h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
              reconciliation?.math_valid ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400"
            }`}
          >
            <Calculator className="h-4 w-4" />
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-200">Integridad Matemática</p>
            <p className="text-[11px] text-gray-400 mt-0.5">
              {reconciliation?.math_valid ? "Subtotal + IGV = Total exacto" : "Descuadre en importes de factura"}
            </p>
          </div>
        </div>

        {/* Pillar 2: Goods */}
        <div className="p-4 rounded-xl bg-[#1e293b]/40 border border-gray-800 flex items-start gap-3">
          <div
            className={`h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
              reconciliation?.goods_matched ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400"
            }`}
          >
            <Package className="h-4 w-4" />
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-200">Recepción de Mercadería</p>
            <p className="text-[11px] text-gray-400 mt-0.5">
              {reconciliation?.goods_matched ? "Cantidades coinciden con Guía" : "Faltante o pendiente de entrega"}
            </p>
          </div>
        </div>

        {/* Pillar 3: Payment */}
        <div className="p-4 rounded-xl bg-[#1e293b]/40 border border-gray-800 flex items-start gap-3">
          <div
            className={`h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
              reconciliation?.payment_matched ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400"
            }`}
          >
            <DollarSign className="h-4 w-4" />
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-200">Conciliación Bancaria</p>
            <p className="text-[11px] text-gray-400 mt-0.5">
              {reconciliation?.payment_matched ? "Voucher cubre el 100% facturado" : "Saldo pendiente o sin voucher"}
            </p>
          </div>
        </div>
      </div>

      {/* Discrepancies Details List */}
      {reconciliation?.discrepancies && reconciliation.discrepancies.length > 0 && (
        <div className="space-y-3 pt-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-rose-400 flex items-center gap-1.5">
            <ShieldAlert className="h-4 w-4" />
            <span>Detalle de Discrepancias Detectadas ({reconciliation.discrepancies.length})</span>
          </h4>

          <div className="space-y-2">
            {reconciliation.discrepancies.map((disc, idx) => (
              <div
                key={idx}
                className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-xs flex items-start justify-between"
              >
                <div>
                  <span className="font-mono font-bold text-rose-300">{disc.type}</span>
                  {disc.item_description && (
                    <p className="text-gray-300 mt-1">
                      Ítem: <span className="font-semibold">{disc.item_description}</span> — Facturado: {disc.billed_quantity}{" "}
                      | Recibido: {disc.received_quantity}
                    </p>
                  )}
                  {disc.balance_pending !== undefined && (
                    <p className="text-gray-300 mt-1">
                      Facturado: S/ {disc.billed_total} | Pagado: S/ {disc.paid_total} |{" "}
                      <span className="text-rose-400 font-bold">Saldo Pendiente: S/ {disc.balance_pending}</span>
                    </p>
                  )}
                  {disc.invoice_currency && (
                    <p className="text-gray-300 mt-1">
                      Inconsistencia: Factura en {disc.invoice_currency} vs. Voucher en {disc.voucher_currency}
                    </p>
                  )}
                </div>

                {disc.shortage && (
                  <span className="px-2 py-1 rounded bg-rose-500/20 text-rose-300 font-mono font-bold">
                    -{disc.shortage} u.
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
