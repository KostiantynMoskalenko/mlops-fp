{{- define "postgres.fullname" -}}
{{- printf "%s-postgres" .Release.Name -}}
{{- end -}}
