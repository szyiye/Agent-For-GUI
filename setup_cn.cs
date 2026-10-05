using System;
using System.Collections;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Reflection;
using System.Resources;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Win32;

namespace AIControllerSetup
{
    public class SetupForm : Form
    {
        private static readonly Color GT = Color.FromArgb(100, 180, 240);
        private static readonly Color GM = Color.FromArgb(140, 200, 250);
        private static readonly Color GB = Color.FromArgb(185, 225, 255);
        private static readonly Color TP = Color.FromArgb(20, 50, 100);
        private static readonly Color TS = Color.FromArgb(70, 110, 160);
        private static readonly Color PB = Color.White;
        private static readonly Color PBd = Color.FromArgb(170, 205, 240);
        private static readonly Color SG = Color.FromArgb(30, 160, 80);

        private Panel pW, pD, pG, pF;
        private Label lWB, lPS, lDB;
        private TextBox tDir;
        private FlatBtn bB, bN, bC, bO;
        private Panel pProg;
        private int page = 0, pv = 0;
        private string dir;
        private bool un;

        public SetupForm(bool u)
        {
            un = u;
            Text = u ? "AI Controller 卸载程序" : "AI Controller 安装程序";
            ClientSize = new Size(580, 440);
            StartPosition = FormStartPosition.CenterScreen;
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false; MinimizeBox = false;
            Font = new Font("Microsoft YaHei UI", 9.5F);
            DoubleBuffered = true;
            SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.UserPaint | ControlStyles.OptimizedDoubleBuffer, true);
            dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "AI Controller");

            var t = new Label(); t.Text = "AI Controller";
            t.Font = new Font("Microsoft YaHei UI", 16F, FontStyle.Bold); t.ForeColor = TP;
            t.BackColor = Color.Transparent; t.Location = new Point(30, 22); t.Size = new Size(400, 32);
            Controls.Add(t);
            var v = new Label(); v.Text = u ? "" : "v2.0  |  全自动电脑控制助手";
            v.Font = new Font("Microsoft YaHei UI", 9F); v.ForeColor = TS;
            v.BackColor = Color.Transparent; v.Location = new Point(32, 54); v.Size = new Size(400, 18);
            Controls.Add(v);
            var sp = new Label(); sp.BackColor = PBd; sp.Location = new Point(30, 80); sp.Size = new Size(520, 1);
            Controls.Add(sp);

            // ===== 第1页：欢迎 =====
            pW = Mk(30, 95, 520, 250);
            MkL(u ? "卸载 AI Controller" : "欢迎使用", 13F, 24, 22, pW);
            lWB = MkL(u
                ? "此程序将从您的计算机中卸载 AI Controller。\r\n\r\n点击「卸载」按钮移除所有已安装的文件。"
                : "此程序将在您的计算机上安装 AI Controller。\r\n\r\nAI Controller 是一款全自动电脑控制助手，\r\n通过 AI 指令操作您的电脑。\r\n\r\n安装完成后，首次运行时配置向导将\r\n引导您完成 API 配置。\r\n\r\n点击「下一步」继续。", 9.5F, 24, 60, pW);

            // ===== 第2页：选择位置 =====
            pD = Mk(30, 95, 520, 250);
            MkL("选择安装位置", 13F, 24, 22, pD);
            MkL("请选择 AI Controller 的安装文件夹：", 9.5F, 24, 58, pD);
            tDir = new TextBox(); tDir.Text = dir; tDir.Font = new Font("Consolas", 10F);
            tDir.Location = new Point(24, 90); tDir.Size = new Size(380, 28);
            tDir.BackColor = Color.FromArgb(235, 243, 252); tDir.ForeColor = TP;
            tDir.BorderStyle = BorderStyle.FixedSingle; pD.Controls.Add(tDir);
            var bBr = new FlatBtn("浏览...", 414, 89, 80, 30);
            bBr.Click += (s, e) => { using (var d = new FolderBrowserDialog()) { d.Description = "选择安装文件夹"; d.SelectedPath = tDir.Text; if (d.ShowDialog() == DialogResult.OK) tDir.Text = d.SelectedPath; } };
            pD.Controls.Add(bBr);
            MkL("提示：建议安装到非系统目录以避免权限问题。", 8.5F, 24, 130, pD);

            // ===== 第3页：安装进度 =====
            pG = Mk(30, 95, 520, 250);
            MkL(u ? "正在卸载..." : "正在安装...", 13F, 24, 22, pG);
            lPS = MkL("准备中...", 9.5F, 24, 65, pG);
            lPS.ForeColor = TS; pG.Controls.Add(lPS);
            pProg = new Panel(); pProg.Location = new Point(24, 100); pProg.Size = new Size(470, 32);
            pProg.BackColor = Color.FromArgb(220, 235, 250);
            pProg.Paint += (s, e) => {
                var g = e.Graphics; g.SmoothingMode = SmoothingMode.AntiAlias;
                var r = new RectangleF(0, 0, pProg.Width, pProg.Height);
                var bp = RR(r, 10);
                using (var b = new SolidBrush(Color.FromArgb(220, 235, 250))) g.FillPath(b, bp);
                float pct = (float)pv / 100f;
                if (pct > 0) { var fr = new RectangleF(0, 0, r.Width * pct, r.Height); var fp = RR(fr, 10); using (var fb = new LinearGradientBrush(fr, Color.FromArgb(50, 130, 210), Color.FromArgb(100, 175, 235), LinearGradientMode.Horizontal)) g.FillPath(fb, fp); }
            };
            pG.Controls.Add(pProg);

            // ===== 第4页：完成 =====
            pF = Mk(30, 95, 520, 250);
            var fh = MkL(u ? "卸载完成！" : "安装完成！", 14F, 24, 30, pF); fh.ForeColor = SG;
            lDB = MkL("", 9.5F, 24, 75, pF);
            bO = new FlatBtn("打开文件夹", 24, 185, 130, 32);
            bO.Click += (s, e) => Process.Start("explorer.exe", dir);
            pF.Controls.Add(bO);

            // ===== 导航按钮 =====
            bB = new FlatBtn("< 返回", 300, 375, 85, 34);
            bB.Click += (s, e) => { if (page > 0 && page < 3) SP(page - 1); };
            Controls.Add(bB);
            bN = new FlatBtn(u ? "卸载" : "下一步 >", 395, 375, 90, 34);
            bN.Font = new Font("Microsoft YaHei UI", 9.5F, FontStyle.Bold);
            bN.Click += BN_Click; Controls.Add(bN);
            bC = new FlatBtn("取消", 495, 375, 70, 34);
            bC.Click += (s, e) => Close(); Controls.Add(bC);

            SP(0);
        }

        protected override void OnPaintBackground(PaintEventArgs e)
        {
            using (var br = new LinearGradientBrush(ClientRectangle, GT, GB, LinearGradientMode.Vertical))
            { var cb = new ColorBlend(3); cb.Colors = new[] { GT, GM, GB }; cb.Positions = new[] { 0f, 0.5f, 1f }; br.InterpolationColors = cb; e.Graphics.FillRectangle(br, ClientRectangle); }
        }

        private void SP(int p)
        {
            page = p;
            pW.Visible = p == 0; pD.Visible = p == 1; pG.Visible = p == 2; pF.Visible = p == 3;
            bB.Visible = p >= 1 && p <= 2; bN.Visible = true;
            bN.Text = p == 3 ? "完成" : (p == 1 ? "安装" : (un && p == 0 ? "卸载" : "下一步 >"));
            bN.Enabled = p != 2; bB.Enabled = p != 2;
        }

        private void BN_Click(object s, EventArgs e)
        {
            if (page == 0) { if (un) { SP(2); new Thread(DU) { IsBackground = true }.Start(); } else SP(1); }
            else if (page == 1) {
                dir = tDir.Text.Trim();
                if (string.IsNullOrEmpty(dir)) { MessageBox.Show("请选择安装目录。", "提示", MessageBoxButtons.OK, MessageBoxIcon.Warning); return; }
                try { Directory.CreateDirectory(dir); } catch (Exception ex) { MessageBox.Show("无法创建目录：\n" + dir + "\n\n" + ex.Message + "\n\n请尝试以管理员身份运行。", "错误", MessageBoxButtons.OK, MessageBoxIcon.Error); return; }
                SP(2); new Thread(DI) { IsBackground = true }.Start();
            }
            else if (page == 3) Close();
        }

        private void DI()
        {
            try {
                string[] fs = { "AI_Controller.exe", "config.ini", "system_prompt.txt", "config_wizard.exe" };
                var asm = Assembly.GetExecutingAssembly();
                var rs = asm.GetManifestResourceStream("app.resources");
                if (rs == null) { SS("错误：未找到内置资源！"); return; }
                var rd = new ResourceReader(rs); var ht = new Hashtable();
                var en = rd.GetEnumerator(); while (en.MoveNext()) ht[(string)en.Key] = (byte[])en.Value;
                rd.Close();
                for (int i = 0; i < fs.Length; i++) {
                    SS("正在安装 " + fs[i] + " ...");
                    string fn = fs[i];
                    if (!ht.ContainsKey(fn)) { foreach (DictionaryEntry de in ht) { if (string.Equals((string)de.Key, fn, StringComparison.OrdinalIgnoreCase)) { fn = (string)de.Key; break; } } }
                    if (ht.ContainsKey(fn)) { File.WriteAllBytes(Path.Combine(dir, fs[i]), (byte[])ht[fn]); PV(((i + 1) * 100) / fs.Length); }
                }
                SS("正在创建卸载程序..."); File.Copy(Application.ExecutablePath, Path.Combine(dir, "uninstaller.exe"), true);
                SS("正在创建桌面快捷方式...");
                try { string d = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory); var p = new ProcessStartInfo("powershell.exe", "-NoProfile -Command \"$ws=New-Object -ComObject WScript.Shell;$sc=$ws.CreateShortcut('" + Path.Combine(d, "AI Controller.lnk") + "');$sc.TargetPath='" + Path.Combine(dir, "AI_Controller.exe") + "';$sc.WorkingDirectory='" + dir + "';$sc.Save()\""); p.UseShellExecute = false; p.CreateNoWindow = true; Process.Start(p).WaitForExit(10000); } catch { }
                SS("正在注册到应用程序列表..."); RU(dir);
                PV(100); SS("完成！");
                BeginInvoke((MethodInvoker)delegate { lDB.Text = "AI Controller 已成功安装到：\r\n" + dir + "\r\n\r\n已创建桌面快捷方式。\r\n已注册到 Windows 应用程序列表。\r\n\r\n首次运行时，配置向导将引导您\r\n完成 API 配置。"; SP(3); });
            } catch (Exception ex) { BeginInvoke((MethodInvoker)delegate { SS("错误：" + ex.Message); SP(1); }); }
        }

        private void DU()
        {
            try {
                string[] fs = { "AI_Controller.exe", "config.ini", "system_prompt.txt", "config_wizard.exe", "uninstaller.exe" };
                for (int i = 0; i < fs.Length; i++) { SS("正在删除 " + fs[i] + " ..."); string p = Path.Combine(dir, fs[i]); if (File.Exists(p)) File.Delete(p); PV(((i + 1) * 80) / fs.Length); }
                string sc = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "AI Controller.lnk");
                if (File.Exists(sc)) File.Delete(sc); PV(85); SS("正在清理注册表..."); RU2(); PV(90);
                SS("正在删除安装目录..."); try { Directory.Delete(dir, true); } catch { } PV(100); SS("完成！");
                BeginInvoke((MethodInvoker)delegate { lDB.Text = "AI Controller 已成功卸载。\r\n\r\n所有文件已从以下位置移除：\r\n" + dir; SP(3); });
            } catch (Exception ex) { BeginInvoke((MethodInvoker)delegate { SS("错误：" + ex.Message); SP(0); }); }
        }

        private void RU(string d)
        {
            try { RegistryKey bk = null; try { bk = Registry.LocalMachine.OpenSubKey(@"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", true); } catch { }
                if (bk == null) bk = Registry.CurrentUser.OpenSubKey(@"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", true);
                if (bk == null) return;
                var ak = bk.CreateSubKey("AI Controller");
                ak.SetValue("DisplayName", "AI Controller"); ak.SetValue("DisplayVersion", "2.0");
                ak.SetValue("Publisher", "AI Controller 项目"); ak.SetValue("InstallLocation", d);
                ak.SetValue("DisplayIcon", Path.Combine(d, "AI_Controller.exe"));
                ak.SetValue("UninstallString", "\"" + Path.Combine(d, "uninstaller.exe") + "\"");
                ak.SetValue("EstimatedSize", 24000, RegistryValueKind.DWord);
                ak.SetValue("NoModify", 1, RegistryValueKind.DWord); ak.SetValue("NoRepair", 1, RegistryValueKind.DWord);
                ak.Close(); bk.Close(); } catch { }
        }

        private void RU2()
        {
            try { var k = Registry.LocalMachine.OpenSubKey(@"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", true); if (k != null) { if (k.OpenSubKey("AI Controller") != null) k.DeleteSubKeyTree("AI Controller", false); k.Close(); } } catch { }
            try { var k = Registry.CurrentUser.OpenSubKey(@"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", true); if (k != null) { if (k.OpenSubKey("AI Controller") != null) k.DeleteSubKeyTree("AI Controller", false); k.Close(); } } catch { }
        }

        private Panel Mk(int x, int y, int w, int h) { var p = new Panel(); p.Location = new Point(x, y); p.Size = new Size(w, h); p.BackColor = PB; p.BorderStyle = BorderStyle.FixedSingle; Controls.Add(p); return p; }
        private Label MkL(string tx, float fs, int x, int y, Control par) { var l = new Label(); l.Text = tx; l.Font = new Font("Microsoft YaHei UI", fs); l.ForeColor = TP; l.BackColor = Color.Transparent; l.Location = new Point(x, y); l.AutoSize = true; par.Controls.Add(l); return l; }
        private static GraphicsPath RR(RectangleF b, float r) { float d = r * 2; var p = new GraphicsPath(); p.AddArc(b.X, b.Y, d, d, 180, 90); p.AddArc(b.Right - d, b.Y, d, d, 270, 90); p.AddArc(b.Right - d, b.Bottom - d, d, d, 0, 90); p.AddArc(b.X, b.Bottom - d, d, d, 90, 90); p.CloseFigure(); return p; }
        private void PV(int v) { pv = Math.Min(100, Math.Max(0, v)); pProg.Invalidate(); }
        private void SS(string tx) { if (lPS.InvokeRequired) lPS.Invoke((MethodInvoker)delegate { lPS.Text = tx; }); else lPS.Text = tx; }
    }

    public class FlatBtn : Button
    {
        private bool h, p;
        public FlatBtn(string text, int x, int y, int w, int h)
        { Text = text; Location = new Point(x, y); Size = new Size(w, h); FlatStyle = FlatStyle.Flat; FlatAppearance.BorderSize = 0; BackColor = Color.FromArgb(50, 130, 210); ForeColor = Color.White; Font = new Font("Microsoft YaHei UI", 9.5F); Cursor = Cursors.Hand; SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.UserPaint | ControlStyles.OptimizedDoubleBuffer, true); MouseEnter += (s, e) => { this.h = true; Invalidate(); }; MouseLeave += (s, e) => { this.h = false; this.p = false; Invalidate(); }; MouseDown += (s, e) => { this.p = true; Invalidate(); }; MouseUp += (s, e) => { this.p = false; Invalidate(); }; }
        protected override void OnPaint(PaintEventArgs e)
        { var g = e.Graphics; g.SmoothingMode = SmoothingMode.AntiAlias; var r = new RectangleF(0, 0, Width - 1, Height - 1); var pa = RR(r, 8); Color bg = p ? Color.FromArgb(40, 110, 190) : (h ? Color.FromArgb(70, 150, 225) : Color.FromArgb(50, 130, 210)); using (var b = new SolidBrush(bg)) g.FillPath(b, pa); using (var pe = new Pen(Color.FromArgb(40, 110, 190), 1f)) g.DrawPath(pe, pa); TextRenderer.DrawText(g, Text, Font, ClientRectangle, ForeColor, TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter); }
        private static GraphicsPath RR(RectangleF b, float r) { float d = r * 2; var p = new GraphicsPath(); p.AddArc(b.X, b.Y, d, d, 180, 90); p.AddArc(b.Right - d, b.Y, d, d, 270, 90); p.AddArc(b.Right - d, b.Bottom - d, d, d, 0, 90); p.AddArc(b.X, b.Bottom - d, d, d, 90, 90); p.CloseFigure(); return p; }
    }

    public static class Program
    {
        [STAThread]
        public static void Main(string[] args)
        {
            Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
            bool u = false; foreach (string a in args) { if (a.ToLower() == "/uninstall" || a.ToLower() == "-uninstall") { u = true; break; } }
            Application.Run(new SetupForm(u));
        }
    }
}
