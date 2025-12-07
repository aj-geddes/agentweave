{{/*
Expand the name of the chart.
*/}}
{{- define "agentweave.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "agentweave.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "agentweave.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "agentweave.labels" -}}
helm.sh/chart: {{ include "agentweave.chart" . }}
{{ include "agentweave.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: agentweave-sdk
{{- end }}

{{/*
Selector labels
*/}}
{{- define "agentweave.selectorLabels" -}}
app.kubernetes.io/name: {{ include "agentweave.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "agentweave.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "agentweave.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the ConfigMap to use
*/}}
{{- define "agentweave.configMapName" -}}
{{- if .Values.config.name }}
{{- .Values.config.name }}
{{- else }}
{{- printf "%s-config" (include "agentweave.fullname" .) }}
{{- end }}
{{- end }}

{{/*
SPIFFE ID for this agent
*/}}
{{- define "agentweave.spiffeId" -}}
{{- printf "spiffe://%s/agent/%s/%s" .Values.global.trustDomain .Values.agent.name .Values.agent.environment }}
{{- end }}
