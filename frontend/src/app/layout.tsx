import type { Metadata } from "next";
import Navbar from "@/components/Navbar";
import "./globals.css";

export const metadata: Metadata = {
  title: "DocuMind Financial AI - Motor de Inteligencia Documental y Cotejo de 3 Vías",
  description:
    "Plataforma de inteligencia contable para cuentas por pagar: conciliación automática de Facturas, Guías de Remisión y Vouchers con OCR espacial acelerado por GPU.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <head>
        <meta name="color-scheme" content="light dark" />
      </head>
      <body className="min-h-screen flex flex-col antialiased">
        <Navbar />
        <main className="flex-1">{children}</main>
      </body>
    </html>
  );
}
