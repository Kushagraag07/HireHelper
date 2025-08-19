import { NextResponse } from "next/server";
import { createClient } from "@deepgram/sdk";

export async function GET() {
  // Use the correct env name and destructure result
 
  const dg = createClient(process.env.DEEPGRAM_API_KEY!);
  const { result, error } = await dg.auth.grantToken();
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
  const access_token = result.access_token;
  return NextResponse.json({ token: access_token });
}
