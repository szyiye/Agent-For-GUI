using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Windows.Forms;

namespace ConfigWizard
{
    public class WizardForm : Form
    {
        private static readonly Color GradTop = Color.FromArgb(100, 180, 240);
        private static readonly Color GradMid = Color.FromArgb(140, 200, 250);
        private static readonly Color GradBot = Color.FromArgb(185, 225, 255);
        private static readonly Color TextPri = Color.FromArgb(20, 50, 100);
        private static readonly Color TextSec = Color.FromArgb(70, 110, 160);
        private static readonly Color PanelBg = Color.White;
        private static readonly Color PanelBorder = Color.FromArgb(170, 205, 240);
        private static readonly Color OkGreen = Color.FromArgb(30, 160, 80);
        private static readonly Color ErrRed = Color.FromArgb(180, 40, 40);

        private Panel panel;
        private ComboBox cmbFormat;
        private TextBox txtUrl, txtKey;
        private ComboBox cmbModel;
        private FlatBtn btnFetchModels;
        private ComboBox cmbThink;
        private TextBox txtPrompt;
        private FlatBtn btnSave;
        private Label lblStatus;

        private string configDir, configPath, promptPath;

        private const string DEFAULT_PROMPT =
            "你是全自动电脑控制助手。你的任务是自主操作用户的电脑完成目标，全程不需要询问用户。\r\n\r\n" +
            "核心规则（必须严格遵守）：\r\n" +
            "1. 你每次回复必须包含至少一个操作命令，或者输出 {wait 秒数} 表示等待，或者输出 {stop} 表示任务已完成。\r\n" +
            "2. 你绝不允许向用户提问、请求确认或等待用户输入。你必须自己决定下一步操作。\r\n" +
            "3. 不确定当前屏幕状态时，先输出 {print screen} 获取屏幕截图。\r\n" +
            "4. 系统会把截图以文字描述或图片形式返回给你，你根据屏幕信息决定下一步操作。\r\n" +
            "5. 每次命令执行后，系统会告诉你执行结果，你接着输出下一个命令。\r\n" +
            "6. 任务完成后输出 {stop}，并在命令前面用一句话总结你做了什么。\r\n" +
            "7. 操作优先级：优先使用GUI操作，其次才使用CLI命令。\r\n\r\n" +
            "可用命令：\r\n" +
            "1. {print screen} - 截取当前屏幕\r\n" +
            "2. {movemouse x,y} - 移动鼠标\r\n" +
            "3. {clickmouse left/right/middle} - 点击鼠标\r\n" +
            "4. {clickbutton 按键名} - 点击键盘按键\r\n" +
            "5. {long-clickmouse left/right/middle 秒} - 长按鼠标\r\n" +
            "6. {long-clickbutton 按键名 秒} - 长按键盘按键\r\n" +
            "7. {more_clickbutton 按键1 按键2 ...} - 组合键\r\n" +
            "8. {addfile 文件路径 文件内容} - 写入文件\r\n" +
            "9. {delfile 文件路径} - 删除文件\r\n" +
            "10. {run cmd/powershell 指令} - 运行命令\r\n" +
            "11. {list_tasks system/user/all} - 进程列表\r\n" +
            "12. {search_tasks 关键词} - 搜索进程\r\n" +
            "13. {print window PID/进程名/路径} - 窗口截图\r\n" +
            "14. {smtc pause/play/previous/next} - 媒体控制\r\n" +
            "15. {list_smtc} - 列出正在播放的媒体\r\n" +
            "16. {wait 秒数} - 等待\r\n" +
            "17. {stop} - 结束任务\r\n\r\n" +
            "坐标系统：截图使用原始分辨率，坐标直接可用。\r\n" +
            "执行流程：截图指令自动放在最后执行。\r\n" +
            "请用中文回复，每次回复开头用一句话说明你要做什么，然后输出命令。\r\n";

        public WizardForm()
        {
            configDir = AppDomain.CurrentDomain.BaseDirectory;
            configPath = Path.Combine(configDir, "config.ini");
            promptPath = Path.Combine(configDir, "system_prompt.txt");

            this.Text = "AI Controller - Initial Setup";
            this.ClientSize = new Size(520, 640);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false; this.MinimizeBox = false;
            this.Font = new Font("Segoe UI", 9.5F);
            this.DoubleBuffered = true;
            this.SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.UserPaint | ControlStyles.OptimizedDoubleBuffer, true);

            var title = new Label();
            title.Text = "AI Controller Setup";
            title.Font = new Font("Segoe UI", 15F, FontStyle.Bold);
            title.ForeColor = TextPri; title.BackColor = Color.Transparent;
            title.Location = new Point(25, 15); title.Size = new Size(400, 30);
            this.Controls.Add(title);

            var sub = new Label();
            sub.Text = "Configure your AI API connection";
            sub.Font = new Font("Segoe UI", 9F);
            sub.ForeColor = TextSec; sub.BackColor = Color.Transparent;
            sub.Location = new Point(27, 45); sub.Size = new Size(400, 16);
            this.Controls.Add(sub);

            var sep = new Label();
            sep.BackColor = PanelBorder; sep.Location = new Point(25, 66); sep.Size = new Size(470, 1);
            this.Controls.Add(sep);

            panel = new Panel();
            panel.Location = new Point(25, 80);
            panel.Size = new Size(470, 490);
            panel.BackColor = PanelBg;
            panel.Paint += (s, e) => {
                var g = e.Graphics; g.SmoothingMode = SmoothingMode.AntiAlias;
                g.DrawPath(new Pen(PanelBorder, 1.5f), RR(new RectangleF(0, 0, panel.Width - 1, panel.Height - 1), 12));
            };
            this.Controls.Add(panel);

            int y = 18;

            ML("API Format:", 24, y); y += 22;
            cmbFormat = MC(24, y, 420);
            cmbFormat.Items.Add("OpenAI-compatible (OpenAI, DeepSeek, MiMo, etc.)");
            cmbFormat.Items.Add("Anthropic-compatible (Claude)");
            cmbFormat.SelectedIndex = 0;
            cmbFormat.SelectedIndexChanged += (s, e) => {
                if (cmbFormat.SelectedIndex == 1) {
                    if (string.IsNullOrWhiteSpace(txtUrl.Text) || txtUrl.Text.Contains("openai") || txtUrl.Text.Contains("xiaomimimo"))
                        txtUrl.Text = "https://api.anthropic.com/v1";
                    if (string.IsNullOrWhiteSpace(cmbModel.Text) || cmbModel.Text.Contains("gpt") || cmbModel.Text.Contains("mimo"))
                        cmbModel.Text = "claude-sonnet-4-20250514";
                    btnFetchModels.Enabled = false;
                } else {
                    if (string.IsNullOrWhiteSpace(txtUrl.Text) || txtUrl.Text.Contains("anthropic"))
                        txtUrl.Text = "https://api.openai.com/v1";
                    if (string.IsNullOrWhiteSpace(cmbModel.Text) || cmbModel.Text.Contains("claude"))
                        cmbModel.Text = "gpt-4o";
                    btnFetchModels.Enabled = true;
                }
            };
            y += 34;

            ML("API URL:", 24, y); y += 22;
            txtUrl = MT(24, y, 420);
            txtUrl.Text = "https://api.openai.com/v1";
            y += 34;

            ML("API Key:", 24, y); y += 22;
            txtKey = MT(24, y, 420);
            txtKey.UseSystemPasswordChar = true;
            y += 34;

            ML("Model:", 24, y); y += 22;
            cmbModel = new ComboBox();
            cmbModel.DropDownStyle = ComboBoxStyle.DropDown;
            cmbModel.Location = new Point(24, y);
            cmbModel.Size = new Size(310, 26);
            cmbModel.Font = new Font("Consolas", 10F);
            cmbModel.BackColor = Color.FromArgb(235, 243, 252);
            cmbModel.ForeColor = TextPri;
            panel.Controls.Add(cmbModel);

            btnFetchModels = new FlatBtn("Fetch Models", 342, y - 1, 102, 28);
            btnFetchModels.Font = new Font("Segoe UI", 8.5F);
            btnFetchModels.Click += BtnFetchModels_Click;
            panel.Controls.Add(btnFetchModels);
            y += 36;

            ML("Thinking Mode:", 24, y); y += 22;
            cmbThink = MC(24, y, 420);
            cmbThink.Items.Add("Default (recommended)");
            cmbThink.Items.Add("Medium");
            cmbThink.SelectedIndex = 0;
            y += 34;

            ML("Custom Prompt (optional, leave empty for default):", 24, y); y += 22;
            txtPrompt = new TextBox();
            txtPrompt.Multiline = true; txtPrompt.ScrollBars = ScrollBars.Vertical;
            txtPrompt.WordWrap = true;
            txtPrompt.Location = new Point(24, y); txtPrompt.Size = new Size(420, 130);
            txtPrompt.Font = new Font("Consolas", 9F);
            txtPrompt.BackColor = Color.FromArgb(235, 243, 252);
            txtPrompt.ForeColor = TextPri; txtPrompt.BorderStyle = BorderStyle.FixedSingle;
            panel.Controls.Add(txtPrompt);
            y += 140;

            btnSave = new FlatBtn("Save & Continue", 155, y, 160, 36);
            btnSave.Font = new Font("Segoe UI", 10F, FontStyle.Bold);
            btnSave.Click += BtnSave_Click;
            panel.Controls.Add(btnSave);

            lblStatus = new Label();
            lblStatus.Text = "Enter your API details, then click Fetch Models to load available models.";
            lblStatus.Font = new Font("Segoe UI", 8.5F);
            lblStatus.ForeColor = TextSec; lblStatus.BackColor = Color.Transparent;
            lblStatus.Location = new Point(25, 580); lblStatus.Size = new Size(470, 45);
            lblStatus.TextAlign = ContentAlignment.TopCenter;
            this.Controls.Add(lblStatus);

            LoadExistingConfig();
        }

        private void BtnFetchModels_Click(object sender, EventArgs e)
        {
            string url = txtUrl.Text.Trim().TrimEnd('/');
            string key = txtKey.Text.Trim();
            if (string.IsNullOrEmpty(url) || string.IsNullOrEmpty(key))
            { SS("Please enter API URL and API Key first.", ErrRed); return; }
            btnFetchModels.Enabled = false;
            btnFetchModels.Text = "Loading...";
            SS("Fetching models from " + url + "/models ...", TextSec);
            string fetchUrl = url;
            Thread t = new Thread(() => FetchModels(fetchUrl, key));
            t.IsBackground = true;
            t.Start();
        }

        private void FetchModels(string baseUrl, string apiKey)
        {
            try {
                try { System.Net.ServicePointManager.SecurityProtocol |= (System.Net.SecurityProtocolType)3072; } catch { }
                string json;
                using (var client = new System.Net.WebClient())
                {
                    client.Headers.Add("Authorization", "Bearer " + apiKey);
                    client.Encoding = Encoding.UTF8;
                    json = client.DownloadString(baseUrl + "/models");
                }
                List<string> models = new List<string>();
                foreach (Match m in Regex.Matches(json, "\"id\"\\s*:\\s*\"([^\"]+)\""))
                { string id = m.Groups[1].Value; if (!string.IsNullOrEmpty(id) && id != "list" && id != "model") models.Add(id); }
                List<string> owners = new List<string>();
                foreach (Match m in Regex.Matches(json, "\"owned_by\"\\s*:\\s*\"([^\"]+)\"")) owners.Add(m.Groups[1].Value);

                if (models.Count == 0 && json.Contains("\"error\""))
                {
                    Match errMatch = Regex.Match(json, "\"message\"\\s*:\\s*\"([^\"]+)\"");
                    string errMsg = errMatch.Success ? errMatch.Groups[1].Value : "Unknown API error";
                    this.BeginInvoke((MethodInvoker)delegate { SS("API Error: " + errMsg, ErrRed); btnFetchModels.Enabled = true; btnFetchModels.Text = "Fetch Models"; });
                    return;
                }

                this.BeginInvoke((MethodInvoker)delegate {
                    cmbModel.Items.Clear();
                    for (int i = 0; i < models.Count; i++)
                    { string display = models[i]; if (i < owners.Count && !string.IsNullOrEmpty(owners[i])) display = models[i] + "  (" + owners[i] + ")"; cmbModel.Items.Add(display); }
                    if (cmbModel.Items.Count > 0) { cmbModel.SelectedIndex = 0; SS("Found " + cmbModel.Items.Count + " models. Select one from the dropdown.", OkGreen); }
                    else SS("No models found. You can type a model name manually.", TextSec);
                    btnFetchModels.Enabled = true; btnFetchModels.Text = "Fetch Models";
                });
            }
            catch (Exception ex) {
                this.BeginInvoke((MethodInvoker)delegate { SS("Error: " + ex.Message, ErrRed); btnFetchModels.Enabled = true; btnFetchModels.Text = "Fetch Models"; });
            }
        }

        private void BtnSave_Click(object sender, EventArgs e)
        {
            string url = txtUrl.Text.Trim();
            string key = txtKey.Text.Trim();
            string model = cmbModel.Text.Trim();
            int parenIdx = model.IndexOf("  (");
            if (parenIdx > 0) model = model.Substring(0, parenIdx).Trim();
            string fmt = cmbFormat.SelectedIndex == 1 ? "anthropic" : "openai";
            string think = cmbThink.SelectedIndex == 1 ? "medium" : "default";

            if (string.IsNullOrEmpty(url)) { SS("Please enter an API URL.", ErrRed); return; }
            if (string.IsNullOrEmpty(key)) { SS("Please enter an API Key.", ErrRed); return; }
            if (string.IsNullOrEmpty(model)) { SS("Please enter or select a Model.", ErrRed); return; }

            try {
                string promptContent = txtPrompt.Text;
                promptContent = promptContent.TrimStart('\r', '\n', ' ', '\t').TrimEnd('\r', '\n', ' ', '\t');
                if (string.IsNullOrEmpty(promptContent)) promptContent = DEFAULT_PROMPT;
                promptContent = promptContent.Replace("\r\n", "\n").Replace("\n", "\r\n");
                File.WriteAllText(promptPath, promptContent, Encoding.UTF8);

                Dictionary<string, string> existing = File.Exists(configPath) ? ReadIniFile(configPath) : new Dictionary<string, string>();
                StringBuilder sb = new StringBuilder();
                sb.AppendLine("[api]");
                sb.AppendLine("api_url = " + url);
                sb.AppendLine("api_key = " + key);
                sb.AppendLine("model = " + model);
                sb.AppendLine("api_format = " + fmt);
                sb.AppendLine("thinking_mode = " + think);
                sb.AppendLine("transcribe_model = " + GetVal(existing, "api", "transcribe_model", "mimo-v2.5"));
                sb.AppendLine("transcribe_api_url = " + GetVal(existing, "api", "transcribe_api_url", ""));
                sb.AppendLine("transcribe_api_key = " + GetVal(existing, "api", "transcribe_api_key", ""));
                sb.AppendLine("use_transcribe = " + GetVal(existing, "api", "use_transcribe", "true"));
                sb.AppendLine();
                sb.AppendLine("[prompts]");
                sb.AppendLine("system_prompt_file = system_prompt.txt");
                sb.AppendLine("default_prompt = " + GetVal(existing, "prompts", "default_prompt", "请帮我查看当前屏幕内容，并告诉我你看到了什么。"));
                sb.AppendLine();
                sb.AppendLine("[settings]");
                sb.AppendLine("screenshot_temp = " + GetVal(existing, "settings", "screenshot_temp", "temp_screenshot.png"));
                sb.AppendLine("screenshot_quality = " + GetVal(existing, "settings", "screenshot_quality", "80"));
                sb.AppendLine("max_image_width = " + GetVal(existing, "settings", "max_image_width", "0"));
                sb.AppendLine("command_delay = " + GetVal(existing, "settings", "command_delay", "0.3"));
                sb.AppendLine("auto_execute = " + GetVal(existing, "settings", "auto_execute", "true"));
                sb.AppendLine("max_turns = " + GetVal(existing, "settings", "max_turns", "100"));
                File.WriteAllText(configPath, sb.ToString(), Encoding.UTF8);

                SS("Configuration saved! Closing...", OkGreen);
                btnSave.Enabled = false; btnSave.Text = "Saved!";
                var timer = new System.Windows.Forms.Timer();
                timer.Interval = 2000;
                timer.Tick += (s, args) => { timer.Stop(); this.Close(); };
                timer.Start();
            }
            catch (Exception ex) { SS("Error: " + ex.Message, ErrRed); }
        }

        private void LoadExistingConfig()
        {
            try {
                if (!File.Exists(configPath)) return;
                var cfg = ReadIniFile(configPath);
                string url = GetVal(cfg, "api", "api_url");
                string key = GetVal(cfg, "api", "api_key");
                string model = GetVal(cfg, "api", "model");
                string fmt = GetVal(cfg, "api", "api_format");
                string think = GetVal(cfg, "api", "thinking_mode");
                if (!string.IsNullOrEmpty(url)) txtUrl.Text = url;
                if (!string.IsNullOrEmpty(key)) txtKey.Text = key;
                if (!string.IsNullOrEmpty(model)) cmbModel.Text = model;
                if (fmt == "anthropic") { cmbFormat.SelectedIndex = 1; btnFetchModels.Enabled = false; }
                else if (fmt == "openai") cmbFormat.SelectedIndex = 0;
                if (think == "medium") cmbThink.SelectedIndex = 1; else cmbThink.SelectedIndex = 0;
                if (File.Exists(promptPath)) {
                    string existing = File.ReadAllText(promptPath, Encoding.UTF8);
                    existing = existing.TrimStart('\r', '\n', ' ', '\t').TrimEnd('\r', '\n', ' ', '\t');
                    if (!string.IsNullOrEmpty(existing)) txtPrompt.Text = existing;
                }
            }
            catch { }
        }

        private Dictionary<string, string> ReadIniFile(string path)
        {
            var dict = new Dictionary<string, string>();
            string section = "";
            foreach (string line in File.ReadAllLines(path, Encoding.UTF8))
            {
                string t = line.Trim();
                if (t.StartsWith("[") && t.EndsWith("]")) { section = t.Substring(1, t.Length - 2).Trim(); continue; }
                int eq = t.IndexOf('=');
                if (eq > 0 && !t.StartsWith("#") && !t.StartsWith(";"))
                    dict[section + "." + t.Substring(0, eq).Trim()] = t.Substring(eq + 1).Trim();
            }
            return dict;
        }

        private string GetVal(Dictionary<string, string> dict, string section, string key, string def = "")
        { string k = section + "." + key; return dict.ContainsKey(k) ? dict[k] : def; }

        protected override void OnPaintBackground(PaintEventArgs e)
        {
            using (var brush = new LinearGradientBrush(this.ClientRectangle, GradTop, GradBot, LinearGradientMode.Vertical))
            { var blend = new ColorBlend(3); blend.Colors = new[] { GradTop, GradMid, GradBot }; blend.Positions = new[] { 0f, 0.5f, 1f }; brush.InterpolationColors = blend; e.Graphics.FillRectangle(brush, this.ClientRectangle); }
        }

        private void ML(string text, int x, int y)
        { var l = new Label(); l.Text = text; l.Font = new Font("Segoe UI", 9F, FontStyle.Bold); l.ForeColor = TextPri; l.BackColor = Color.Transparent; l.Location = new Point(x, y); l.Size = new Size(420, 18); panel.Controls.Add(l); }

        private TextBox MT(int x, int y, int w)
        { var t = new TextBox(); t.Location = new Point(x, y); t.Size = new Size(w, 26); t.Font = new Font("Consolas", 10F); t.BackColor = Color.FromArgb(235, 243, 252); t.ForeColor = TextPri; t.BorderStyle = BorderStyle.FixedSingle; panel.Controls.Add(t); return t; }

        private ComboBox MC(int x, int y, int w)
        { var c = new ComboBox(); c.DropDownStyle = ComboBoxStyle.DropDownList; c.Location = new Point(x, y); c.Size = new Size(w, 26); c.Font = new Font("Segoe UI", 9.5F); c.BackColor = Color.FromArgb(235, 243, 252); c.ForeColor = TextPri; panel.Controls.Add(c); return c; }

        private void SS(string text, Color color)
        { if (lblStatus.InvokeRequired) lblStatus.Invoke((MethodInvoker)delegate { lblStatus.Text = text; lblStatus.ForeColor = color; }); else { lblStatus.Text = text; lblStatus.ForeColor = color; } }

        private static GraphicsPath RR(RectangleF b, float r)
        { float d = r * 2; var p = new GraphicsPath(); p.AddArc(b.X, b.Y, d, d, 180, 90); p.AddArc(b.Right - d, b.Y, d, d, 270, 90); p.AddArc(b.Right - d, b.Bottom - d, d, d, 0, 90); p.AddArc(b.X, b.Bottom - d, d, d, 90, 90); p.CloseFigure(); return p; }
    }

    public class FlatBtn : Button
    {
        private bool h, p;
        public FlatBtn(string text, int x, int y, int w, int h)
        { Text = text; Location = new Point(x, y); Size = new Size(w, h); FlatStyle = FlatStyle.Flat; FlatAppearance.BorderSize = 0; BackColor = Color.FromArgb(50, 130, 210); ForeColor = Color.White; Font = new Font("Segoe UI", 9.5F); Cursor = Cursors.Hand; SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.UserPaint | ControlStyles.OptimizedDoubleBuffer, true); MouseEnter += (s, e) => { this.h = true; Invalidate(); }; MouseLeave += (s, e) => { this.h = false; this.p = false; Invalidate(); }; MouseDown += (s, e) => { this.p = true; Invalidate(); }; MouseUp += (s, e) => { this.p = false; Invalidate(); }; }
        protected override void OnPaint(PaintEventArgs e)
        { var g = e.Graphics; g.SmoothingMode = SmoothingMode.AntiAlias; var r = new RectangleF(0, 0, Width - 1, Height - 1); var pa = RR(r, 8); Color bg = p ? Color.FromArgb(40, 110, 190) : (h ? Color.FromArgb(70, 150, 225) : Color.FromArgb(50, 130, 210)); using (var b = new SolidBrush(bg)) g.FillPath(b, pa); using (var pe = new Pen(Color.FromArgb(40, 110, 190), 1f)) g.DrawPath(pe, pa); TextRenderer.DrawText(g, Text, Font, ClientRectangle, ForeColor, TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter); }
        private static GraphicsPath RR(RectangleF b, float r) { float d = r * 2; var p = new GraphicsPath(); p.AddArc(b.X, b.Y, d, d, 180, 90); p.AddArc(b.Right - d, b.Y, d, d, 270, 90); p.AddArc(b.Right - d, b.Bottom - d, d, d, 0, 90); p.AddArc(b.X, b.Bottom - d, d, d, 90, 90); p.CloseFigure(); return p; }
    }

    public static class Program
    {
        [STAThread]
        public static void Main()
        {
            try { System.Net.ServicePointManager.SecurityProtocol |= (System.Net.SecurityProtocolType)3072; } catch { }
            Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new WizardForm());
        }
    }
}
