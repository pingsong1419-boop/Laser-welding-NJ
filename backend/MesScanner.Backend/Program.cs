using System.Diagnostics;
using System.Text;
using System.Net.Sockets;
using Microsoft.Extensions.FileProviders;

var builder = WebApplication.CreateBuilder(args);

// 显式配置监听地址（确保发布模式也使用 5246 端口）
builder.WebHost.UseUrls("http://localhost:5246");

// 1. 注册服务
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowAll", policy =>
    {
        policy.AllowAnyHeader()
              .AllowAnyMethod()
              .SetIsOriginAllowed(_ => true)
              .AllowCredentials();
    });
});

var app = builder.Build();

// 2. 配置中间件
app.UseCors("AllowAll");

// 3. 使用嵌入的静态文件（前端 Vue 构建产物已打包进 EXE）
var assembly = typeof(Program).Assembly;
var embeddedProvider = new EmbeddedFileProvider(assembly, "MesScanner.Backend.wwwroot");
app.UseStaticFiles(new StaticFileOptions { FileProvider = embeddedProvider });

// 4. 业务 API
app.MapGet("/api", () => "MES Module Packing Backend Running...");

// 保存日志到本地文件
app.MapPost("/api/saveLogs", async (LogSaveRequest req) =>
{
    try 
    {
        string savePath = string.IsNullOrEmpty(req.Path) ? "C:\\NJ_Torque_Logs" : req.Path;
        if (!Directory.Exists(savePath)) Directory.CreateDirectory(savePath);
        
        string fullPath = Path.Combine(savePath, req.FileName);
        await File.WriteAllTextAsync(fullPath, req.Content);
        return Results.Ok(new { message = "Save success", path = fullPath });
    }
    catch (Exception ex)
    {
        return Results.Problem(ex.Message);
    }
});

// 打印标签（Zebra ZT510 默认走 TCP 9100 + ZPL）
app.MapPost("/api/printLabels", async (PrintLabelsRequest req) =>
{
    if (string.IsNullOrWhiteSpace(req.PrinterIp))
    {
        return Results.Ok(new { code = 400, message = "打印机IP不能为空", printedCount = 0 });
    }

    var labels = req.Labels?
        .Where(l => !string.IsNullOrWhiteSpace(l.Code))
        .ToList() ?? new List<PrintLabelItem>();

    if (labels.Count == 0)
    {
        return Results.Ok(new { code = 400, message = "没有可打印的条码", printedCount = 0 });
    }

    var printerPort = req.PrinterPort > 0 ? req.PrinterPort : 9100;
    var copies = req.Copies > 0 ? req.Copies : 1;
    var printedCount = 0;

    try
    {
        using var client = new TcpClient();
        await client.ConnectAsync(req.PrinterIp, printerPort);
        await using var stream = client.GetStream();

        foreach (var label in labels)
        {
            for (var i = 0; i < copies; i++)
            {
                var zpl = BuildZplLabel(label);
                var bytes = Encoding.UTF8.GetBytes(zpl);
                await stream.WriteAsync(bytes);
                printedCount++;
            }
        }

        await stream.FlushAsync();

        return Results.Ok(new
        {
            code = 200,
            message = $"打印请求成功，已发送 {printedCount} 张",
            printedCount
        });
    }
    catch (Exception ex)
    {
        return Results.Ok(new
        {
            code = 500,
            message = $"打印失败: {ex.Message}",
            printedCount
        });
    }
});

// 5. SPA 回退：所有未匹配路由返回 index.html（支持 Vue Router 刷新）
app.MapFallbackToFile("index.html", new StaticFileOptions { FileProvider = embeddedProvider });

// 6. 自动打开浏览器（延迟执行，等待服务器就绪）
_ = Task.Run(async () =>
{
    await Task.Delay(2000);
    var url = app.Urls.FirstOrDefault() ?? "http://localhost:5246";
    try
    {
        Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
    }
    catch { /* 忽略打开浏览器失败 */ }
});

app.Run();

static string BuildZplLabel(PrintLabelItem label)
{
    var code = SanitizeZplText(label.Code);
    var labelType = SanitizeZplText(string.IsNullOrWhiteSpace(label.LabelType) ? "条码" : label.LabelType);

    return $"""
^XA
^CI28
^PW799
^LL400
^FO40,30^A0N,40,40^FD{labelType}^FS
^FO40,95^A0N,34,34^FD{code}^FS
^BY3,2,120
^FO40,150^BCN,120,Y,N,N^FD{code}^FS
^XZ
""";
}

static string SanitizeZplText(string text)
{
    return text
        .Replace("^", " ")
        .Replace("~", " ")
        .Replace("\r", " ")
        .Replace("\n", " ")
        .Trim();
}

public record LogSaveRequest(string FileName, string Content, string Path);

public record PrintLabelsRequest(
    string PrinterIp,
    int PrinterPort,
    List<PrintLabelItem> Labels,
    int Copies
);

public record PrintLabelItem(string Code, string LabelType);
