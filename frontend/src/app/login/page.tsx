import type { Metadata } from "next";
import LoginForm from "@/components/app/LoginForm";

export const metadata: Metadata = { title: { absolute: "Sign in, chatbot0" }, robots: { index: false } };

export default function Page() {
  return <LoginForm />;
}
