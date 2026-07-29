export interface PortalSubmitResponse {
  reference: string
  status: string
  progress_stage: string
  ai_message: string | null
  citations: string[]
}

export interface PortalMessage {
  author: string
  body: string
}

export interface PortalTrackResponse {
  reference: string
  status: string
  progress_stage: string
  channel: string
  messages: PortalMessage[]
}
