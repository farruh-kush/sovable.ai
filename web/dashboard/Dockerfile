FROM nginx:1.27-alpine
COPY web/dashboard/nginx.conf /etc/nginx/conf.d/default.conf
COPY web/dashboard/site/ /usr/share/nginx/html/
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:8080/health || exit 1
