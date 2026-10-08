import { Suspense } from "react";
import { Loading } from "@/components/ui";
import View from "./view";

export default function Page() {
  return (
    <Suspense fallback={<Loading />}>
      <View />
    </Suspense>
  );
}
