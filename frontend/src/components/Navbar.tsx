"use client";

import React, { useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { FileStack, Plus, X } from "lucide-react";
import DossierUpload from "./DossierUpload";

export default function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const isHome = pathname === "/";
  const dialogRef = useRef<HTMLDialogElement>(null);

  // Fallback for browsers without native dialog[closedby="any"] support (light-dismiss-a-dialog guide)
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const handleCustomOpen = () => {
      if (!dialog.open) dialog.showModal();
    };
    window.addEventListener("documind:open-upload-modal", handleCustomOpen);

    let cleanupClick: (() => void) | undefined;
    if (!("closedBy" in HTMLDialogElement.prototype)) {
      const onClick = (event: MouseEvent) => {
        if (event.target !== dialog) return;
        const rect = dialog.getBoundingClientRect();
        const isDialogContent =
          rect.top <= event.clientY &&
          event.clientY <= rect.top + rect.height &&
          rect.left <= event.clientX &&
          event.clientX <= rect.left + rect.width;
        if (isDialogContent) return;
        dialog.close();
      };
      dialog.addEventListener("click", onClick);
      cleanupClick = () => dialog.removeEventListener("click", onClick);
    }

    return () => {
      window.removeEventListener("documind:open-upload-modal", handleCustomOpen);
      cleanupClick?.();
    };
  }, []);

  const openModal = () => {
    dialogRef.current?.showModal();
  };

  return (
    <>
      <header className="top-bar">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2.5 flex items-center justify-between gap-4">
          {/* Brand & Navigation */}
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-2 group focus:outline-none">
              <span className="font-bold text-zinc-100 text-lg tracking-tight group-hover:text-amber-400 transition">
                DocuMind
              </span>
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500 shadow-[0_0_8px_#f59e0b]" aria-hidden="true" />
              <span className="text-xs text-zinc-400 font-medium hidden sm:inline">
                Cuentas por Pagar
              </span>
            </Link>

            <nav aria-label="Navegación principal" className="flex items-center gap-1">
              <Link
                href="/"
                aria-current={isHome ? "page" : undefined}
                className="nav-link text-xs font-medium"
              >
                <FileStack className="h-3.5 w-3.5" aria-hidden="true" />
                <span>Expedientes</span>
              </Link>
            </nav>
          </div>

          {/* New Audit Modal Trigger */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={openModal}
              className="accent-button inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition active:scale-95 shadow-sm shadow-amber-950/40"
            >
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Nueva Auditoría</span>
            </button>
          </div>
        </div>
      </header>

      {/* Native Modal Dialog with Smooth Scale & Fade Animation */}
      <dialog
        ref={dialogRef}
        {...({ closedby: "any" } as any)}
        aria-labelledby="modal-upload-title"
        className="modal-animated"
      >
        <div className="p-5 sm:p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
            <div>
              <h2 id="modal-upload-title" className="text-base font-bold text-zinc-100">
                Nueva Auditoría de Expediente
              </h2>
              <p className="text-xs text-zinc-400">
                Adjunta Factura, Guía y Voucher para iniciar el cotejo de 3 vías.
              </p>
            </div>
            <form method="dialog">
              <button
                type="submit"
                aria-label="Cerrar ventana"
                className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 transition"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </form>
          </div>

          <DossierUpload
            onDossierUploaded={(dossierId) => {
              dialogRef.current?.close();
              window.dispatchEvent(new CustomEvent("documind:dossier-created", { detail: dossierId }));
              router.push(`/dossier/${dossierId}`);
            }}
          />
        </div>
      </dialog>
    </>
  );
}
