package com.example.stealthmark;

import okhttp3.*;
import org.json.JSONObject;
import org.json.JSONArray;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.TimeUnit;

/**
 * StealthMark Java HTTP 客户端示例
 *
 * 依赖（ Maven pom.xml）：
 * <pre>
 * &lt;dependency&gt;
 *     &lt;groupId&gt;com.squareup.okhttp3&lt;/groupId&gt;
 *     &lt;artifactId&gt;okhttp&lt;/artifactId&gt;
 *     &lt;version&gt;4.12.0&lt;/version&gt;
 * &lt;/dependency&gt;
 * &lt;dependency&gt;
 *     &lt;groupId&gt;org.json&lt;/groupId&gt;
 *     &lt;artifactId&gt;json&lt;/artifactId&gt;
 *     &lt;version&gt;20240303&lt;/version&gt;
 * &lt;/dependency&gt;
 * </pre>
 *
 * 也可用内置 javax.net.ssl（HttpsURLConnection），不需要第三方依赖。
 * 所有方法均兼容 Java 11+ 内置 HTTP 客户端（java.net.http.HttpClient）。
 */
public class StealthMarkDemo {

    // ════════════════════════════════════════════════════════
    // 配置区 - 根据你的部署环境修改
    // ════════════════════════════════════════════════════════

    /** StealthMark API 地址（生产环境改为 HTTPS） */
    private static final String BASE_URL = "http://localhost:8001";

    /** 并发嵌入时的文件类型映射（扩展名 → MIME） */
    private static final Map<String, String> MIME_TYPES = new HashMap<>();
    static {
        MIME_TYPES.put("png",  "image/png");
        MIME_TYPES.put("jpg",  "image/jpeg");
        MIME_TYPES.put("jpeg", "image/jpeg");
        MIME_TYPES.put("pdf",  "application/pdf");
        MIME_TYPES.put("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
        MIME_TYPES.put("mp4",  "video/mp4");
        MIME_TYPES.put("mp3",  "audio/mpeg");
        MIME_TYPES.put("wav",  "audio/wav");
    }

    // ════════════════════════════════════════════════════════
    // 核心 HTTP 客户端（单例，连接池复用）
    // ════════════════════════════════════════════════════════

    private final OkHttpClient client;

    public StealthMarkDemo() {
        this.client = new OkHttpClient.Builder()
                .connectTimeout(30, TimeUnit.SECONDS)   // 连接超时
                .readTimeout(60, TimeUnit.SECONDS)      // 读取超时
                .writeTimeout(60, TimeUnit.SECONDS)     // 写入超时
                .connectionPool(new ConnectionPool(10, 5, TimeUnit.MINUTES))
                .retryOnConnectionFailure(true)
                .build();
    }

    // ════════════════════════════════════════════════════════
    // 第一步：生成水印 JSON
    // ════════════════════════════════════════════════════════

    /**
     * 生成结构化水印内容。
     *
     * @param author   作者/机构 DID
     * @param org      版权组织名称
     * @param workId   作品唯一标识
     * @param type     水印类型：copyright | personal | brand
     * @return 服务器返回的完整水印 JSON
     */
    public JSONObject generateWatermark(String author, String org,
                                        String workId, String type) throws IOException {
        JSONObject payload = new JSONObject();
        payload.put("author", author);
        payload.put("org", org);
        payload.put("work_id", workId);
        payload.put("type", type);

        String response = post("/watermark/generate", payload.toString(), "application/json");
        return new JSONObject(response);
    }

    // ════════════════════════════════════════════════════════
    // 第二步：嵌入水印
    // ════════════════════════════════════════════════════════

    /**
     * 将水印嵌入单个文件。
     *
     * @param filePath      文件路径
     * @param watermarkJson 水印 JSON（generateWatermark 返回值）
     * @param robust        是否使用鲁棒模式（抗亮度/对比度/JPEG压缩）
     * @param password      可选加密密码（null = 不加密）
     * @return 输出文件路径
     */
    public String embed(String filePath, JSONObject watermarkJson,
                        boolean robust, String password) throws IOException {
        Path path = Paths.get(filePath);
        byte[] fileBytes = Files.readAllBytes(path);
        String ext = getExtension(filePath).toLowerCase();
        String mime = MIME_TYPES.getOrDefault(ext, "application/octet-stream");

        // 构建 multipart/form-data
        RequestBody fileBody = RequestBody.create(fileBytes,
                MediaType.parse(mime));

        MultipartBody.Builder builder = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", path.getFileName().toString(), fileBody)
                .addFormDataPart("watermark", watermarkJson.toString())
                .addFormDataPart("robust", String.valueOf(robust));

        if (password != null && !password.isEmpty()) {
            builder.addFormDataPart("password", password);
        }

        String response = postMultipart("/embed", builder.build());
        JSONObject json = new JSONObject(response);

        // 从响应中取出输出文件路径（/static/file/xxx）
        String outputUrl = json.getString("file");
        return outputUrl;
    }

    /**
     * 下载已嵌入水印的文件到本地。
     *
     * @param outputUrl  /static/file/... 路径
     * @param savePath   保存目标路径
     */
    public void downloadFile(String outputUrl, String savePath) throws IOException {
        String fullUrl = BASE_URL + outputUrl;
        Request request = new Request.Builder()
                .url(fullUrl)
                .get()
                .build();

        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("下载失败: HTTP " + response.code());
            }
            if (response.body() == null) {
                throw new IOException("响应体为空");
            }
            Files.write(Paths.get(savePath), response.body().bytes());
        }
    }

    // ════════════════════════════════════════════════════════
    // 第三步：提取水印
    // ════════════════════════════════════════════════════════

    /**
     * 从已嵌入文件提取水印。
     *
     * @param filePath  已嵌入水印的文件路径
     * @param password  加密时的密码（null = 不加密）
     * @return 解析后的水印 JSON 对象
     */
    public JSONObject extract(String filePath, String password) throws IOException {
        Path path = Paths.get(filePath);
        byte[] fileBytes = Files.readAllBytes(path);
        String ext = getExtension(filePath).toLowerCase();
        String mime = MIME_TYPES.getOrDefault(ext, "application/octet-stream");

        MultipartBody.Builder builder = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", path.getFileName().toString(),
                        RequestBody.create(fileBytes, MediaType.parse(mime)));

        if (password != null) {
            builder.addFormDataPart("password", password);
        }

        String response = postMultipart("/extract", builder.build());
        JSONObject json = new JSONObject(response);

        // 解析 embedded.watermark 字段（Base64 → JSON）
        JSONObject embedded = json.getJSONObject("embedded");
        String watermarkBase64 = embedded.getString("watermark");
        String watermarkJson = decodeBase64(watermarkBase64);
        return new JSONObject(watermarkJson);
    }

    // ════════════════════════════════════════════════════════
    // 第四步：验证水印
    // ════════════════════════════════════════════════════════

    /**
     * 验证文件是否携带指定水印。
     *
     * @param filePath       已嵌入文件路径
     * @param expectedAuthor 期望的作者 DID
     * @param expectedWorkId  期望的作品 ID
     * @return 是否匹配
     */
    public boolean verify(String filePath, String expectedAuthor,
                          String expectedWorkId) throws IOException {
        Path path = Paths.get(filePath);
        byte[] fileBytes = Files.readAllBytes(path);
        String ext = getExtension(filePath).toLowerCase();
        String mime = MIME_TYPES.getOrDefault(ext, "application/octet-stream");

        MultipartBody.Builder builder = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", path.getFileName().toString(),
                        RequestBody.create(fileBytes, MediaType.parse(mime)));

        String response = postMultipart("/verify", builder.build());
        JSONObject json = new JSONObject(response);

        if (!json.getBoolean("verified")) {
            return false;
        }

        // 进一步校验作者和作品ID
        String watermarkBase64 = json.getJSONObject("embedded").getString("watermark");
        JSONObject wm = new JSONObject(decodeBase64(watermarkBase64));
        return expectedAuthor.equals(wm.optString("author"))
                && expectedWorkId.equals(wm.optString("work_id"));
    }

    // ════════════════════════════════════════════════════════
    // 第五步：批量嵌入
    // ════════════════════════════════════════════════════════

    /**
     * 批量嵌入水印到多个文件。
     *
     * @param filePaths  文件路径列表
     * @param watermark  水印 JSON
     * @param robust     是否鲁棒模式
     * @return 每个文件的嵌入结果
     */
    public List<BatchResult> batch(List<String> filePaths, JSONObject watermark,
                                   boolean robust) throws IOException {
        JSONObject payload = new JSONObject();
        payload.put("files", filePaths);
        payload.put("watermark", watermark);
        payload.put("robust", robust);

        String response = post("/batch", payload.toString(), "application/json");
        JSONObject json = new JSONObject(response);

        List<BatchResult> results = new ArrayList<>();
        JSONArray resultsArray = json.getJSONArray("results");
        for (int i = 0; i < resultsArray.length(); i++) {
            JSONObject item = resultsArray.getJSONObject(i);
            results.add(new BatchResult(
                    item.getString("file"),
                    item.getBoolean("success"),
                    item.optString("error", null)
            ));
        }
        return results;
    }

    public static class BatchResult {
        public final String file;
        public final boolean success;
        public final String error;

        public BatchResult(String file, boolean success, String error) {
            this.file = file;
            this.success = success;
            this.error = error;
        }
    }

    // ════════════════════════════════════════════════════════
    // HTTP 底层调用
    // ════════════════════════════════════════════════════════

    private String post(String path, String jsonBody, String contentType) throws IOException {
        RequestBody body = RequestBody.create(jsonBody,
                MediaType.parse(contentType));
        Request request = new Request.Builder()
                .url(BASE_URL + path)
                .post(body)
                .build();

        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("HTTP " + response.code() + ": " + response.message());
            }
            return response.body() == null ? "" : response.body().string();
        }
    }

    private String postMultipart(String path, RequestBody body) throws IOException {
        Request request = new Request.Builder()
                .url(BASE_URL + path)
                .post(body)
                .build();

        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("HTTP " + response.code() + ": " + response.message());
            }
            return response.body() == null ? "" : response.body().string();
        }
    }

    // ════════════════════════════════════════════════════════
    // 工具方法
    // ════════════════════════════════════════════════════════

    private static String getExtension(String path) {
        int lastDot = path.lastIndexOf('.');
        return lastDot > 0 ? path.substring(lastDot + 1) : "";
    }

    private static String decodeBase64(String base64) throws IOException {
        byte[] data = Base64.getDecoder().decode(base64);
        return new String(data, java.nio.charset.StandardCharsets.UTF_8);
    }

    // ════════════════════════════════════════════════════════
    // 完整流程演示
    // ════════════════════════════════════════════════════════

    public static void main(String[] args) {
        StealthMarkDemo api = new StealthMarkDemo();

        try {
            // ① 生成水印
            JSONObject watermark = api.generateWatermark(
                    "did:example:author123",     // 作者 DID
                    "我的版权组织",                // 版权组织
                    "WORK-2025-001",             // 作品 ID
                    "copyright"                  // 类型
            );
            System.out.println("[生成水印] " + watermark.toString(2));

            String author = watermark.getString("author");
            String workId = watermark.getString("work_id");
            String rawJson = watermark.getJSONObject("watermark").toString();
            System.out.println("[原始 JSON] " + rawJson);

            // ② 嵌入单个文件
            String inputFile = "test.png";
            String outputPath = api.embed(inputFile, watermark, true, null);
            System.out.println("[嵌入成功] " + outputPath);

            // ③ 下载到本地（如果 API 和你的应用不在同一台机器）
            String localFile = "test_watermarked.png";
            api.downloadFile(outputPath, localFile);
            System.out.println("[下载到本地] " + localFile);

            // ④ 提取水印
            JSONObject extracted = api.extract(localFile, null);
            System.out.println("[提取水印] author=" + extracted.optString("author")
                    + ", work_id=" + extracted.optString("work_id"));

            // ⑤ 验证
            boolean ok = api.verify(localFile, author, workId);
            System.out.println("[验证结果] " + (ok ? "✅ 匹配" : "❌ 不匹配"));

            // ⑥ 批量嵌入（示例）
            List<String> files = Arrays.asList("doc1.pdf", "doc2.pdf", "doc3.pdf");
            List<BatchResult> batchResults = api.batch(files, watermark, true);
            for (BatchResult r : batchResults) {
                System.out.println(r.file + " → " + (r.success ? "OK" : "FAIL: " + r.error));
            }

        } catch (IOException e) {
            System.err.println("[错误] " + e.getMessage());
            e.printStackTrace();
        }
    }
}
