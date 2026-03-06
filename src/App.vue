<template>
  <div class="app-container">
    <div class="header-box">
      <div>
        <h2>计算器</h2>
        <p>💡 逻辑：橘色(到达0.382常规买点) | 金色(跌破0.618强撑)；持仓规则：最高点回撤30%止盈 + -7%止损；自动刷新间隔 20 秒</p>
      </div>
      <div style="text-align: right">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px; justify-content: flex-end;">
          <span style="font-size: 12px; color: #909399;">自动刷新(20s)</span>
          <el-switch v-model="autoRefreshEnabled" @change="onAutoRefreshToggle" />
        </div>
        <el-button-group>
          <el-button @click="checkStorage">检测后端</el-button>
          <el-button type="primary" @click="refreshAllPrices" :loading="loading">刷新行情</el-button>
        </el-button-group>
      </div>
    </div>

    <div class="section-wrap">
      <el-tabs v-model="activeTab" stretch>
        <el-tab-pane label="观察列表" name="watchlist">
          <div class="pane-wrap">
            <div class="toolbar">
              <el-input
                v-model="inputCodes"
                type="textarea"
                :rows="2"
                placeholder="输入代码：A股(600519), 港股(700 或 hk700), ETF(510300)"
                style="flex: 1"
              />
              <el-select v-model="watchCategoryFilter" placeholder="按分类查看" style="width: 180px">
                <el-option label="全部分类" value="__all__" />
                <el-option v-for="cat in allWatchCategories" :key="cat" :label="cat" :value="cat" />
              </el-select>
              <el-button type="primary" @click="addNewCodes" :loading="loading" style="height: 52px; width: 120px">
                查询并追加
              </el-button>
              <el-button type="danger" @click="clearWatchlist" style="height: 52px; width: 120px">清空观察</el-button>
            </div>

            <div class="table-wrap">
              <el-table
                ref="stockTableRef"
                row-key="fullCode"
                :data="filteredWatchlist"
                border
                height="100%"
                style="width: 100%"
                v-loading="loading"
                :row-class-name="tableRowClassName"
              >
                <el-table-column prop="name" label="名称/代码" min-width="150" fixed="left">
                  <template #default="scope">
                    <div style="font-weight: bold; color: #303133">
                      <span :class="['market-tag', 'tag-' + getMarket(scope.row.fullCode)]">{{ getMarket(scope.row.fullCode).toUpperCase() }}</span>
                      {{ scope.row.name }}
                    </div>
                    <div style="font-size: 11px; color: #909399; margin-left: 32px">{{ scope.row.fullCode }}</div>
                  </template>
                </el-table-column>

                <el-table-column label="分类" width="140">
                  <template #default="scope">
                    <div style="display: flex; flex-direction: column; gap: 6px;">
                      <div style="display: flex; flex-wrap: wrap; gap: 4px; min-height: 24px;">
                        <el-tag v-for="cat in scope.row.categories" :key="scope.row.fullCode + '-' + cat" size="small">
                          {{ cat }}
                        </el-tag>
                        <span v-if="!scope.row.categories || !scope.row.categories.length" style="font-size: 12px; color: #c0c4cc;">无标签</span>
                      </div>
                      <el-button type="primary" size="small" link @click="openRowCategoryDialog(scope.row)">管理标签</el-button>
                    </div>
                  </template>
                </el-table-column>

                <el-table-column label="最新价" width="120">
                  <template #default="scope">
                    <div :class="['price-block', getDayChangeClass(scope.row)]">
                      <div class="price-now">{{ scope.row.now }}</div>
                      <div class="price-pct">{{ formatDayChangePct(scope.row) }}</div>
                    </div>
                  </template>
                </el-table-column>

                <el-table-column label="E3·高点" width="120">
                  <template #default="scope">
                    <el-input-number
                      v-model="scope.row.high"
                      :precision="3"
                      :controls="false"
                      size="small"
                      style="width: 100%"
                      @change="onFieldChange(scope.row, 'high')"
                    />
                  </template>
                </el-table-column>

                <el-table-column label="D3·低点" width="120">
                  <template #default="scope">
                    <el-input-number
                      v-model="scope.row.low"
                      :precision="3"
                      :controls="false"
                      size="small"
                      style="width: 100%"
                      @change="onFieldChange(scope.row, 'low')"
                    />
                  </template>
                </el-table-column>

                <el-table-column label="分时均价" width="120">
                  <template #default="scope">
                    <el-input-number
                      v-model="scope.row.avg"
                      :precision="3"
                      :controls="false"
                      size="small"
                      style="width: 100%"
                      @change="onFieldChange(scope.row, 'avg')"
                    />
                  </template>
                </el-table-column>

                <el-table-column label="常规买点" min-width="90">
                  <template #default="scope"><span :class="['fib-val', getFibClass(scope.row, 'f382')]">{{ scope.row.f382 }}</span></template>
                </el-table-column>

                <el-table-column label="618强撑" min-width="90">
                  <template #default="scope"><span :class="['fib-val', getFibClass(scope.row, 'f618')]">{{ scope.row.f618 }}</span></template>
                </el-table-column>

                <el-table-column label="🔴 日内压力" min-width="90">
                  <template #default="scope"><span class="red-text">{{ scope.row.topLine }}</span></template>
                </el-table-column>

                <el-table-column label="🟢 日内支撑" min-width="90">
                  <template #default="scope"><span class="green-text">{{ scope.row.bottomLine }}</span></template>
                </el-table-column>

                <el-table-column label="操作" width="140" fixed="right" align="center">
                  <template #default="scope">
                    <div class="op-wrap">
                      <span class="drag-handle" title="拖动排序">⋮⋮</span>
                      <div class="op-actions">
                        <el-button type="primary" size="small" link @click="togglePin(scope.row)">
                          <span class="op-label">{{ scope.row.isPinned ? "取消置顶" : "置顶" }}</span>
                        </el-button>
                        <el-button type="primary" size="small" link @click="addRowToHoldings(scope.row)"><span class="op-label">加入持仓</span></el-button>
                        <el-button type="primary" size="small" link @click="moveToFront(scope.row)"><span class="op-label">移到最前</span></el-button>
                        <el-button type="danger" size="small" link @click="removeItem(scope.row)"><span class="op-label">删除</span></el-button>
                      </div>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="持仓管理" name="holdings">
          <div class="pane-wrap">
            <div class="toolbar">
              <el-input
                v-model="holdingCodes"
                type="textarea"
                :rows="2"
                placeholder="输入代码：A股(600519), 港股(700 或 hk700), ETF(510300)"
                style="flex: 1"
              />
              <el-button type="primary" @click="importHoldings" :loading="loading" style="height: 52px; width: 120px">查询并追加</el-button>
              <el-button type="danger" @click="clearHoldings" style="height: 52px; width: 120px">清空持仓</el-button>
            </div>

            <div class="table-wrap">
              <el-table row-key="fullCode" :data="holdingsData" border height="100%" style="width: 100%" v-loading="loading" :row-class-name="holdingsRowClassName">
                <el-table-column prop="name" label="名称/代码" min-width="170" fixed="left">
                  <template #default="scope">
                    <div style="font-weight: bold; color: #303133">
                      <span :class="['market-tag', 'tag-' + getMarket(scope.row.fullCode)]">{{ getMarket(scope.row.fullCode).toUpperCase() }}</span>
                      {{ scope.row.name || "--" }}
                    </div>
                    <div style="font-size: 11px; color: #909399; margin-left: 32px">{{ scope.row.fullCode }}</div>
                  </template>
                </el-table-column>
                <el-table-column label="最新价" width="120">
                  <template #default="scope">
                    <div :class="['price-block', getDayChangeClass(scope.row)]">
                      <div class="price-now">{{ scope.row.now }}</div>
                      <div class="price-pct">{{ formatDayChangePct(scope.row) }}</div>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="浮盈亏%" width="110"><template #default="scope"><span :class="getProfitClass(scope.row)">{{ scope.row.pnlRate }}%</span></template></el-table-column>
                <el-table-column label="持仓后最高" width="110">
                  <template #default="scope">
                    <el-input-number
                      v-model="scope.row.highest"
                      :precision="3"
                      :controls="false"
                      size="small"
                      style="width: 100%"
                      @change="onHoldingHighestChange(scope.row)"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="关键监控位" min-width="180">
                  <template #default="scope">
                    <div :class="['monitor-wrap', getMonitorClass(scope.row)]">
                      <div class="monitor-price">{{ scope.row.monitorPriceText || "--" }}</div>
                      <div class="monitor-desc">{{ scope.row.monitorDesc || "--" }}</div>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="信号" min-width="150">
                  <template #default="scope">
                    <el-tag :type="scope.row.ruleSignalType || 'success'">{{ scope.row.ruleSignalText || "持有" }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="规则" width="130">
                  <template #default="scope">
                    <el-select v-model="scope.row.ruleType" size="small" @change="onHoldingFieldChange(scope.row)">
                      <el-option label="规则1 20%回撤止盈" value="r1" />
                      <el-option label="规则2 13日验证" value="r2" />
                    </el-select>
                  </template>
                </el-table-column>
                <el-table-column label="买入日期" width="150">
                  <template #default="scope">
                    <el-date-picker
                      v-model="scope.row.buyDate"
                      type="date"
                      value-format="YYYY-MM-DD"
                      format="YYYY-MM-DD"
                      size="small"
                      style="width: 100%"
                      @change="onHoldingFieldChange(scope.row)"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="波段低点" width="120">
                  <template #default="scope">
                    <el-input-number
                      v-model="scope.row.swingLow"
                      :precision="3"
                      :controls="false"
                      size="small"
                      style="width: 100%"
                      @change="onHoldingFieldChange(scope.row)"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="参考新高" width="120">
                  <template #default="scope">
                    <el-input-number
                      v-model="scope.row.refHigh"
                      :precision="3"
                      :controls="false"
                      size="small"
                      style="width: 100%"
                      @change="onHoldingFieldChange(scope.row)"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="成本价" width="120"><template #default="scope"><el-input-number v-model="scope.row.cost" :precision="3" :controls="false" size="small" style="width: 100%" @change="onHoldingFieldChange(scope.row)" /></template></el-table-column>
                <el-table-column label="数量" width="120"><template #default="scope"><el-input-number v-model="scope.row.quantity" :precision="0" :controls="false" size="small" style="width: 100%" @change="onHoldingFieldChange(scope.row)" /></template></el-table-column>
                <el-table-column label="操作" width="90" fixed="right" align="center"><template #default="scope"><el-button type="danger" size="small" link @click="removeHolding(scope.$index)">删除</el-button></template></el-table-column>
              </el-table>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="分类管理" name="categories">
          <div class="pane-wrap">
            <div class="toolbar">
              <el-input v-model="newCategoryName" placeholder="输入新分类名" style="flex: 1" @keyup.enter="addWatchCategory" />
              <el-button type="primary" @click="addWatchCategory" style="height: 40px; width: 120px;">新增分类</el-button>
            </div>
            <div class="table-wrap" style="min-height: 220px;">
              <el-table :data="categoryManageRows" border height="100%" style="width: 100%">
                <el-table-column prop="name" label="分类名" min-width="220" />
                <el-table-column prop="count" label="关联股票数" width="140" />
                <el-table-column label="操作" width="180" align="center">
                  <template #default="scope">
                    <el-button type="primary" size="small" link @click="renameWatchCategory(scope.row.name)">重命名</el-button>
                    <el-button type="danger" size="small" link @click="deleteWatchCategory(scope.row.name)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <div class="toolbar" style="margin-top: 16px;">
              <el-date-picker v-model="newHolidayDate" type="date" value-format="YYYY-MM-DD" format="YYYY-MM-DD" placeholder="选择休市日期" style="width: 180px;" />
              <el-input v-model="newHolidayNote" placeholder="休市备注(可选)" style="flex: 1" />
              <el-button type="primary" @click="addHoliday" style="height: 40px; width: 120px;">新增休市日</el-button>
            </div>
            <div style="height: 220px;">
              <el-table :data="holidayRows" border height="100%" style="width: 100%">
                <el-table-column prop="date" label="休市日期" width="160" />
                <el-table-column prop="note" label="备注" min-width="180" />
                <el-table-column label="操作" width="120" align="center">
                  <template #default="scope">
                    <el-button type="danger" size="small" link @click="deleteHoliday(scope.row.date)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-dialog v-model="rowCategoryDialogVisible" title="管理股票标签" width="520px">
      <div style="display: flex; flex-direction: column; gap: 12px;">
        <div>
          <div style="font-size: 12px; color: #909399; margin-bottom: 8px;">已选标签</div>
          <el-checkbox-group v-model="rowCategorySelection">
            <el-checkbox v-for="cat in allWatchCategories" :key="'row-cat-' + cat" :label="cat">{{ cat }}</el-checkbox>
          </el-checkbox-group>
        </div>
        <div style="display: flex; gap: 8px;">
          <el-input v-model="rowNewCategoryName" placeholder="新增并选中标签" @keyup.enter="addCategoryInRowDialog" />
          <el-button type="primary" @click="addCategoryInRowDialog">新增标签</el-button>
        </div>
      </div>
      <template #footer>
        <el-button @click="rowCategoryDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveRowCategoryDialog">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import Sortable from "sortablejs";

const defaultApiBase = window.location.protocol === "file:" ? "http://127.0.0.1:8765/api" : "/api";
const API_BASE = (import.meta.env.VITE_API_BASE || defaultApiBase).replace(/\/+$/, "");
const LOCAL_KEY = "phi_batch_table_v6";
const REFRESH_MS = 20000;
const K = 0.98848;

const activeTab = ref("watchlist");
const watchCategoryFilter = ref("__all__");
const inputCodes = ref("");
const holdingCodes = ref("");
const autoRefreshEnabled = ref(true);
const watchCategories = ref([]);
const newCategoryName = ref("");
const holidayRows = ref([]);
const newHolidayDate = ref("");
const newHolidayNote = ref("");
const rowCategoryDialogVisible = ref(false);
const editingRowCode = ref("");
const rowCategorySelection = ref([]);
const rowNewCategoryName = ref("");
const tableData = ref([]);
const holdingsData = ref([]);
const loading = ref(false);
const stockTableRef = ref(null);
let rowSortable = null;
let refreshTimer = null;
let saveTimer = null;

const isValidNumber = (value) => Number.isFinite(parseFloat(value));
const safeNum = (value, fallback = 0) => {
  const n = parseFloat(value);
  return Number.isFinite(n) ? n : fallback;
};

const FALLBACK_2026_HOLIDAYS = [
  "2026-01-01","2026-01-02","2026-01-03",
  "2026-02-15","2026-02-16","2026-02-17","2026-02-18","2026-02-19","2026-02-20","2026-02-21","2026-02-22","2026-02-23",
  "2026-04-04","2026-04-05","2026-04-06",
  "2026-05-01","2026-05-02","2026-05-03","2026-05-04","2026-05-05",
  "2026-06-19","2026-06-20","2026-06-21",
  "2026-09-25","2026-09-26","2026-09-27",
  "2026-10-01","2026-10-02","2026-10-03","2026-10-04","2026-10-05","2026-10-06","2026-10-07"
];

const holidayDateSet = computed(() => new Set((holidayRows.value || []).map((row) => row.date)));

const todayStr = () => {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
};

const parseDateYmd = (dateStr) => {
  if (!dateStr || !/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return null;
  const [y, m, d] = dateStr.split("-").map((v) => parseInt(v, 10));
  const dt = new Date(y, m - 1, d);
  if (dt.getFullYear() !== y || dt.getMonth() !== m - 1 || dt.getDate() !== d) return null;
  return dt;
};

const toYmd = (dt) => {
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, "0");
  const d = String(dt.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
};

const isTradingDay = (dt) => {
  const weekday = dt.getDay();
  if (weekday === 0 || weekday === 6) return false;
  return !holidayDateSet.value.has(toYmd(dt));
};

const tradingDaysSince = (dateStr) => {
  const start = parseDateYmd(dateStr);
  if (!start) return null;
  const now = new Date();
  const end = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (start.getTime() > end.getTime()) return 0;

  let cnt = 0;
  const cur = new Date(start.getFullYear(), start.getMonth(), start.getDate());
  while (cur.getTime() <= end.getTime()) {
    if (isTradingDay(cur)) cnt += 1;
    cur.setDate(cur.getDate() + 1);
  }
  return cnt;
};

const parseLocalState = () => {
  try {
    const raw = localStorage.getItem(LOCAL_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return { watchlist: parsed, holdings: [], watchCategories: [] };
    if (parsed && typeof parsed === "object") {
      return {
        watchlist: Array.isArray(parsed.watchlist) ? parsed.watchlist : [],
        holdings: Array.isArray(parsed.holdings) ? parsed.holdings : [],
        watchCategories: Array.isArray(parsed.watchCategories) ? parsed.watchCategories : []
      };
    }
  } catch {
  }
  return null;
};

const formatCode = (code) => {
  code = String(code || "").trim().toLowerCase();
  if (!code) return null;
  if (/^(sh|sz|hk|bj|s_sh|s_sz)/.test(code)) return code;
  if (/^\d+$/.test(code)) {
    if (code.length <= 4 || (code.length === 5 && code.startsWith("0"))) return "hk" + code.padStart(5, "0");
    if (code.length === 6) {
      if (/^(5[168]|6)/.test(code)) return "sh" + code;
      if (/^(1[568]|0|3)/.test(code)) return "sz" + code;
      if (/^(4|8)/.test(code)) return "bj" + code;
    }
  }
  return code;
};

const calculateRow = (row, shouldSave = true) => {
  const high = parseFloat(row.high);
  const low = parseFloat(row.low);
  const avg = parseFloat(row.avg);

  if (Number.isFinite(high) && Number.isFinite(low)) {
    const diff = high - low;
    row.f382 = (high - diff * 0.382).toFixed(3);
    row.f618 = (high - diff * 0.618).toFixed(3);
    row.f786 = (high - diff * 0.786).toFixed(3);
  } else {
    row.f382 = 0;
    row.f618 = 0;
    row.f786 = 0;
  }

  if (Number.isFinite(avg) && avg > 0) {
    row.topLine = (avg / K).toFixed(3);
    row.bottomLine = (avg * K).toFixed(3);
  } else {
    row.topLine = 0;
    row.bottomLine = 0;
  }

  if (shouldSave) saveStateDebounced();
};

const evaluateHolding = (row, shouldSave = true) => {
  const cost = safeNum(row.cost, 0);
  const now = safeNum(row.now, 0);

  row.highest = now > 0 ? Math.max(safeNum(row.highest, 0), now) : Math.max(safeNum(row.highest, 0), cost);
  if (cost > 0) {
    row.pnlRate = (((now - cost) / cost) * 100).toFixed(2);
    row.stopLossTriggered = now > 0 && now <= cost * 0.93;
  } else {
    row.pnlRate = "0.00";
    row.stopLossTriggered = false;
  }

  const ruleType = row.ruleType || "r1";
  row.ruleSignalType = "success";
  row.ruleSignalText = "持有";
  row.monitorPrice = 0;
  row.monitorPriceText = "--";
  row.monitorDesc = "未激活";
  row.monitorStatus = "neutral";

  if (ruleType === "r2") {
    const daysHeld = tradingDaysSince(row.buyDate);
    const swingLow = safeNum(row.swingLow, 0);
    const refHigh = safeNum(row.refHigh, 0);
    const breachLine = swingLow > 0 ? swingLow * 0.97 : 0;
    const newHighHit = refHigh > 0 ? row.highest >= refHigh : row.highest > cost;
    const in13Days = daysHeld != null && daysHeld <= 13;
    const over13Days = daysHeld != null && daysHeld > 13;

    const breachStop = in13Days && breachLine > 0 && now > 0 && now <= breachLine;
    const timeoutStop = over13Days && !newHighHit;

    row.takeProfitTriggered = false;
    row.stopLossTriggered = breachStop || timeoutStop;
    if (breachLine > 0) {
      row.monitorPrice = breachLine;
      row.monitorPriceText = breachLine.toFixed(3);
    }

    if (daysHeld == null) {
      row.ruleSignalType = "warning";
      row.ruleSignalText = "规则2需设置买入日期";
      row.monitorDesc = "规则2需设置买入日期";
      row.monitorStatus = "warning";
    } else if (row.stopLossTriggered && breachStop) {
      row.ruleSignalType = "danger";
      row.ruleSignalText = "规则2止损: 13个交易日内跌破波段低点-3%";
      row.monitorDesc = "已跌破R2防守线";
      row.monitorStatus = "danger";
    } else if (row.stopLossTriggered && timeoutStop) {
      row.ruleSignalType = "danger";
      row.ruleSignalText = "规则2止损: 13个交易日内未创新高";
      row.monitorDesc = "超13日未创新高";
      row.monitorStatus = "danger";
    } else if (in13Days && !newHighHit) {
      row.ruleSignalType = "warning";
      row.ruleSignalText = `规则2观察中: 第${daysHeld}个交易日`;
      const remainingDays = Math.max(13 - daysHeld, 0);
      if (breachLine > 0 && now > 0) {
        const distPct = ((now - breachLine) / breachLine) * 100;
        row.monitorDesc = `R2防守线 余${remainingDays}天 距离${distPct >= 0 ? "+" : ""}${distPct.toFixed(2)}%`;
        row.monitorStatus = distPct <= 2 ? "warning" : "active";
      } else {
        row.monitorDesc = `R2防守线 余${remainingDays}天`;
        row.monitorStatus = breachLine > 0 ? "active" : "warning";
      }
    } else {
      row.ruleSignalType = "success";
      row.ruleSignalText = "规则2通过";
      if (over13Days) {
        if (newHighHit) {
          row.monitorDesc = "R2已通过13日验证";
          row.monitorStatus = "active";
        } else {
          row.monitorDesc = "R2超13日待创新高";
          row.monitorStatus = "warning";
        }
      } else {
        const remainingDays = Math.max(13 - safeNum(daysHeld, 0), 0);
        row.monitorDesc = `R2已创新高 余${remainingDays}天`;
        row.monitorStatus = "active";
      }
    }
  } else {
    // 规则1：先达到浮盈20%，再按利润回撤30%止盈
    const takeProfitArmed = cost > 0 && row.highest >= cost * 1.2;
    const takeProfitLine = takeProfitArmed ? (cost + (row.highest - cost) * 0.7) : 0;
    row.takeProfitTriggered = takeProfitArmed && now > 0 && now <= takeProfitLine;
    if (row.stopLossTriggered) row.takeProfitTriggered = false;

    if (takeProfitArmed) {
      row.monitorPrice = takeProfitLine;
      row.monitorPriceText = takeProfitLine.toFixed(3);
      if (now > 0 && takeProfitLine > 0) {
        const distPct = ((now - takeProfitLine) / takeProfitLine) * 100;
        row.monitorDesc = `R1止盈线 距离${distPct >= 0 ? "+" : ""}${distPct.toFixed(2)}%`;
        row.monitorStatus = (row.stopLossTriggered || row.takeProfitTriggered) ? "danger" : (distPct <= 2 ? "warning" : "active");
      } else {
        row.monitorDesc = "R1止盈线已激活";
        row.monitorStatus = (row.stopLossTriggered || row.takeProfitTriggered) ? "danger" : "active";
      }
    } else {
      row.monitorDesc = "R1未激活(需先达到浮盈20%)";
      row.monitorStatus = row.stopLossTriggered ? "danger" : "neutral";
    }

    if (row.stopLossTriggered) {
      row.ruleSignalType = "danger";
      row.ruleSignalText = "触发-7%止损";
    } else if (row.takeProfitTriggered) {
      row.ruleSignalType = "warning";
      row.ruleSignalText = "触发30%回撤止盈";
    } else if (takeProfitArmed) {
      row.ruleSignalType = "success";
      row.ruleSignalText = "已启动止盈跟踪";
    } else {
      row.ruleSignalType = "success";
      row.ruleSignalText = "持有";
    }
  }

  if (shouldSave) saveStateDebounced();
};

const toWatchRow = (item) => {
  const categories = Array.isArray(item.categories)
    ? item.categories.filter((v) => v && String(v).trim() && String(v).trim() !== "未分类")
    : (item.category ? String(item.category).split(/[，,]/).map((s) => s.trim()).filter((v) => v && v !== "未分类") : []);
  const row = reactive({
    name: item.name || "",
    fullCode: formatCode(item.fullCode || item.code || ""),
    categories,
    now: safeNum(item.now, 0),
    close: safeNum(item.close, 0),
    high: safeNum(item.high, 0),
    low: safeNum(item.low, 0),
    avg: safeNum(item.avg, 0),
    isPinned: !!item.isPinned,
    manualHigh: !!item.manualHigh,
    manualLow: !!item.manualLow,
    manualAvg: !!item.manualAvg,
    f382: item.f382 || 0,
    f618: item.f618 || 0,
    f786: item.f786 || 0,
    topLine: item.topLine || 0,
    bottomLine: item.bottomLine || 0
  });
  calculateRow(row, false);
  return row;
};

const toHoldingRow = (item) => {
  const cost = safeNum(item.cost, 0);
  const now = safeNum(item.now, 0);
  const highest = Math.max(safeNum(item.highest, 0), now, cost);
  const row = reactive({
    name: item.name || "",
    fullCode: formatCode(item.fullCode || item.code || ""),
    cost,
    quantity: Math.max(0, Math.round(safeNum(item.quantity, 0))),
    ruleType: item.ruleType || "r1",
    buyDate: item.buyDate || "",
    swingLow: safeNum(item.swingLow, 0),
    refHigh: safeNum(item.refHigh, 0),
    now,
    close: safeNum(item.close, 0),
    highest,
    pnlRate: "0.00",
    stopLossTriggered: false,
    takeProfitTriggered: false,
    ruleSignalText: "持有",
    ruleSignalType: "success",
    monitorPrice: 0,
    monitorPriceText: "--",
    monitorDesc: "未激活",
    monitorStatus: "neutral"
  });
  evaluateHolding(row, false);
  return row;
};

const getPayload = () => ({
  watchlist: JSON.parse(JSON.stringify(tableData.value)),
  holdings: JSON.parse(JSON.stringify(holdingsData.value)),
  watchCategories: Array.from(
    new Set((watchCategories.value || []).map((v) => String(v || "").trim()).filter((v) => v && v !== "未分类"))
  )
});

const apiRequest = async (path, options = {}) => {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const text = await res.text();
  let body = null;
  try {
    body = JSON.parse(text);
  } catch {
    if (/^\s*</.test(text)) {
      throw new Error("API返回了HTML而不是JSON（请检查前端 /api 代理或 VITE_API_BASE）");
    }
    throw new Error("API返回了无效JSON");
  }
  if (!body.ok) throw new Error(body.error || "API error");
  return body;
};

const loadHolidayCalendar = async () => {
  try {
    const body = await apiRequest("/calendar/holidays");
    const rows = Array.isArray(body.data) ? body.data : [];
    holidayRows.value = rows.map((r) => ({ date: r.date, note: r.note || "" }));
  } catch {
    holidayRows.value = FALLBACK_2026_HOLIDAYS.map((d) => ({ date: d, note: "2026休市默认" }));
  }
};

const addHoliday = async () => {
  if (!newHolidayDate.value) return;
  try {
    await apiRequest("/calendar/holidays", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date: newHolidayDate.value, note: newHolidayNote.value || "" })
    });
    newHolidayDate.value = "";
    newHolidayNote.value = "";
    await loadHolidayCalendar();
    holdingsData.value.forEach((row) => evaluateHolding(row, false));
    saveStateDebounced();
  } catch (e) {
    ElMessage.error(`新增休市日失败：${e.message || e}`);
  }
};

const deleteHoliday = async (date) => {
  try {
    await apiRequest(`/calendar/holidays?date=${encodeURIComponent(date)}`, { method: "DELETE" });
    await loadHolidayCalendar();
    holdingsData.value.forEach((row) => evaluateHolding(row, false));
    saveStateDebounced();
  } catch (e) {
    ElMessage.error(`删除休市日失败：${e.message || e}`);
  }
};

const loadState = async () => {
  let loaded = null;
  try {
    const body = await apiRequest("/state");
    loaded = body.data;
  } catch {
    loaded = parseLocalState();
  }
  if (!loaded) return;
  tableData.value = (loaded.watchlist || []).map(toWatchRow).filter((r) => r.fullCode);
  holdingsData.value = (loaded.holdings || []).map(toHoldingRow).filter((r) => r.fullCode);
  watchCategories.value = Array.isArray(loaded.watchCategories) ? loaded.watchCategories.filter(Boolean) : [];
  watchCategories.value = watchCategories.value.filter((v) => String(v).trim() && String(v).trim() !== "未分类");
  sortPinnedToTop();
};

const saveState = async () => {
  const payload = getPayload();
  try {
    localStorage.setItem(LOCAL_KEY, JSON.stringify(payload));
  } catch {
  }

  try {
    await apiRequest("/state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data: payload })
    });
  } catch {
  }
};

const saveStateDebounced = () => {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => saveState(), 300);
};

const tableRowClassName = ({ row }) => {
  const now = parseFloat(row.now);
  if (isNaN(now) || !row.f382) return "";
  if (now <= parseFloat(row.f618)) return "warning-row";
  if (now <= parseFloat(row.f382)) return "normal-row";
  return "";
};

const holdingsRowClassName = ({ row }) => {
  if (row.stopLossTriggered) return "danger-row";
  if (row.takeProfitTriggered) return "warning-row";
  return "";
};

const getFibClass = (row, level) => {
  const now = parseFloat(row.now);
  const f382 = parseFloat(row.f382);
  const f618 = parseFloat(row.f618);
  const f786 = parseFloat(row.f786);
  if (isNaN(now) || isNaN(f382) || isNaN(f618) || isNaN(f786)) return "";
  if (level === "f382" && now <= f382) return "fib-hit-382";
  if (level === "f618" && now <= f618) return "fib-hit-618";
  if (level === "f786" && now <= f786) return "fib-hit-786";
  return "";
};

const getMarket = (fullCode) => {
  if (fullCode.startsWith("sh")) return "sh";
  if (fullCode.startsWith("sz")) return "sz";
  if (fullCode.startsWith("hk")) return "hk";
  if (fullCode.startsWith("bj")) return "sz";
  return "sz";
};

const sortPinnedToTop = () => {
  const pinned = tableData.value.filter((i) => i.isPinned);
  const others = tableData.value.filter((i) => !i.isPinned);
  tableData.value = [...pinned, ...others];
};

const allWatchCategories = computed(() => {
  const set = new Set();
  (watchCategories.value || []).forEach((cat) => {
    const val = String(cat || "").trim();
    if (val) set.add(val);
  });
  tableData.value.forEach((row) => {
    (row.categories || []).forEach((cat) => {
      const val = String(cat || "").trim();
      if (val) set.add(val);
    });
  });
  return Array.from(set);
});

const filteredWatchlist = computed(() => {
  if (watchCategoryFilter.value === "__all__") return tableData.value;
  return tableData.value.filter((row) => (row.categories || []).includes(watchCategoryFilter.value));
});

const categoryManageRows = computed(() => {
  return allWatchCategories.value.map((name) => ({
    name,
    count: tableData.value.filter((row) => (row.categories || []).includes(name)).length
  }));
});

const normalizeCategoryName = (value) => String(value || "").trim();

const addCategoryToPool = (name) => {
  const n = normalizeCategoryName(name);
  if (!n) return null;
  if (n === "未分类") return null;
  if (!watchCategories.value.includes(n)) watchCategories.value.push(n);
  return n;
};

const addWatchCategory = () => {
  const candidate = normalizeCategoryName(newCategoryName.value);
  if (!candidate) return;
  if (allWatchCategories.value.includes(candidate)) {
    ElMessage.warning("分类已存在");
    return;
  }
  const n = addCategoryToPool(newCategoryName.value);
  if (!n) return;
  newCategoryName.value = "";
  saveStateDebounced();
};

const renameWatchCategory = async (oldName) => {
  try {
    const { value } = await ElMessageBox.prompt("请输入新的分类名", "重命名分类", {
      inputValue: oldName,
      confirmButtonText: "确定",
      cancelButtonText: "取消"
    });
    const newName = normalizeCategoryName(value);
    if (!newName || newName === oldName) return;
    if (allWatchCategories.value.includes(newName)) {
      ElMessage.warning("分类名已存在");
      return;
    }

    watchCategories.value = watchCategories.value.map((cat) => (cat === oldName ? newName : cat));
    tableData.value.forEach((row) => {
      row.categories = (row.categories || []).map((cat) => (cat === oldName ? newName : cat));
    });
    saveStateDebounced();
  } catch {
  }
};

const deleteWatchCategory = (name) => {
  ElMessageBox.confirm(`确定删除分类“${name}”吗？将从所有股票中移除该标签。`)
    .then(() => {
      watchCategories.value = watchCategories.value.filter((cat) => cat !== name);
      tableData.value.forEach((row) => {
        row.categories = (row.categories || []).filter((cat) => cat !== name);
      });
      if (watchCategoryFilter.value === name) watchCategoryFilter.value = "__all__";
      saveStateDebounced();
    })
    .catch(() => {});
};

const openRowCategoryDialog = (row) => {
  editingRowCode.value = row.fullCode;
  rowCategorySelection.value = [...(row.categories || [])];
  rowNewCategoryName.value = "";
  rowCategoryDialogVisible.value = true;
};

const addCategoryInRowDialog = () => {
  const n = addCategoryToPool(rowNewCategoryName.value);
  if (!n) return;
  if (!rowCategorySelection.value.includes(n)) rowCategorySelection.value.push(n);
  rowNewCategoryName.value = "";
};

const saveRowCategoryDialog = () => {
  const row = tableData.value.find((x) => x.fullCode === editingRowCode.value);
  if (!row) {
    rowCategoryDialogVisible.value = false;
    return;
  }
  row.categories = Array.from(new Set(rowCategorySelection.value.map((v) => normalizeCategoryName(v)).filter(Boolean)));
  rowCategoryDialogVisible.value = false;
  saveStateDebounced();
};

const initRowDrag = () => {
  nextTick(() => {
    const tableEl = stockTableRef.value?.$el;
    const tbody = tableEl?.querySelector(".el-table__body-wrapper tbody");
    if (!tbody) return;
    if (rowSortable) {
      rowSortable.destroy();
      rowSortable = null;
    }
    rowSortable = Sortable.create(tbody, {
      animation: 150,
      handle: ".drag-handle",
      disabled: watchCategoryFilter.value !== "__all__",
      onEnd: ({ oldIndex, newIndex }) => {
        if (oldIndex == null || newIndex == null || oldIndex === newIndex) return;
        const pinnedCountBefore = tableData.value.filter((i) => i.isPinned).length;
        const moved = tableData.value.splice(oldIndex, 1)[0];
        tableData.value.splice(newIndex, 0, moved);
        if (!moved.isPinned && pinnedCountBefore > 0 && newIndex < pinnedCountBefore) moved.isPinned = true;
        sortPinnedToTop();
        saveStateDebounced();
      }
    });
  });
};

const fetchQuotes = async (codes) => {
  const body = await apiRequest("/quotes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ codes })
  });
  return Array.isArray(body.data) ? body.data : [];
};

const refreshAllPrices = async () => {
  const codeSet = new Set();
  tableData.value.forEach((r) => r.fullCode && codeSet.add(r.fullCode));
  holdingsData.value.forEach((r) => r.fullCode && codeSet.add(r.fullCode));
  const allCodes = Array.from(codeSet);
  if (!allCodes.length) return;

  loading.value = true;
  try {
    const quotes = await fetchQuotes(allCodes);
    const quoteMap = new Map(quotes.map((i) => [i.fullCode, i]));

    tableData.value.forEach((row) => {
      const q = quoteMap.get(row.fullCode);
      if (!q) return;
      row.name = q.name || row.name;
      row.now = safeNum(q.now, row.now);
      row.close = safeNum(q.close, row.close);
      if (!row.manualHigh || !isValidNumber(row.high)) row.high = safeNum(q.high, row.now);
      if (!row.manualLow || !isValidNumber(row.low)) row.low = safeNum(q.low, row.now);
      if (!row.manualAvg || !isValidNumber(row.avg)) row.avg = safeNum(q.avg, row.now);
      calculateRow(row, false);
    });

    holdingsData.value.forEach((row) => {
      const q = quoteMap.get(row.fullCode);
      if (!q) return;
      row.name = q.name || row.name;
      row.now = safeNum(q.now, row.now);
      row.close = safeNum(q.close, row.close);
      const qHigh = safeNum(q.high, 0);
      if (qHigh > safeNum(row.highest, 0)) row.highest = qHigh;
      evaluateHolding(row, false);
    });

    saveStateDebounced();
  } catch (e) {
    ElMessage.error(`刷新行情失败：${e.message || e}`);
  } finally {
    loading.value = false;
  }
};

const addNewCodes = async () => {
  const codes = inputCodes.value.split(/[,\s\n]/).map((c) => formatCode(c)).filter(Boolean);
  if (!codes.length) return;

  loading.value = true;
  try {
    const quotes = await fetchQuotes(codes);
    const quoteMap = new Map(quotes.map((i) => [i.fullCode, i]));
    let insertIndex = tableData.value.filter((i) => i.isPinned).length;
    codes.forEach((code) => {
      if (tableData.value.some((i) => i.fullCode === code)) return;
      const q = quoteMap.get(code) || {};
      const now = safeNum(q.now, 0);
      const row = reactive({
        name: q.name || code,
        fullCode: code,
        categories: [],
        now,
        close: safeNum(q.close, now),
        high: safeNum(q.high, now),
        low: safeNum(q.low, now),
        avg: safeNum(q.avg, now),
        isPinned: false,
        manualHigh: false,
        manualLow: false,
        manualAvg: false,
        f382: 0,
        f618: 0,
        f786: 0,
        topLine: 0,
        bottomLine: 0
      });
      calculateRow(row, false);
      tableData.value.splice(insertIndex, 0, row);
      insertIndex += 1;
    });

    inputCodes.value = "";
    saveStateDebounced();
    initRowDrag();
  } catch (e) {
    ElMessage.error(`追加失败：${e.message || e}`);
  } finally {
    loading.value = false;
  }
};

const importHoldings = async () => {
  const codes = holdingCodes.value.split(/[,\s\n]/).map((c) => formatCode(c)).filter(Boolean);
  if (!codes.length) return;

  loading.value = true;
  try {
    const quotes = await fetchQuotes(codes);
    const quoteMap = new Map(quotes.map((i) => [i.fullCode, i]));
    codes.forEach((code) => {
      const existing = holdingsData.value.find((row) => row.fullCode === code);
      const q = quoteMap.get(code) || {};
      const now = safeNum(q.now, 0);

      if (existing) {
        existing.name = q.name || existing.name;
        if (now > 0) existing.now = now;
        const close = safeNum(q.close, 0);
        if (close > 0) existing.close = close;
        evaluateHolding(existing, false);
      } else {
        const row = reactive({
          name: q.name || code,
          fullCode: code,
          cost: 0,
          quantity: 0,
          ruleType: "r1",
          buyDate: todayStr(),
          swingLow: 0,
          refHigh: 0,
          now,
          close: safeNum(q.close, now),
          highest: Math.max(now, 0),
          pnlRate: "0.00",
          stopLossTriggered: false,
          takeProfitTriggered: false,
          ruleSignalText: "持有",
          ruleSignalType: "success",
          monitorPrice: 0,
          monitorPriceText: "--",
          monitorDesc: "未激活",
          monitorStatus: "neutral"
        });
        evaluateHolding(row, false);
        holdingsData.value.unshift(row);
      }
    });

    holdingCodes.value = "";
    saveStateDebounced();
  } catch (e) {
    ElMessage.error(`导入失败：${e.message || e}`);
  } finally {
    loading.value = false;
  }
};

const addRowToHoldings = (watchRow) => {
  const existing = holdingsData.value.find((row) => row.fullCode === watchRow.fullCode);

  if (existing) {
    existing.name = watchRow.name || existing.name;
    existing.now = safeNum(watchRow.now, existing.now);
    existing.close = safeNum(watchRow.close, existing.close);
    if (!safeNum(existing.swingLow, 0)) existing.swingLow = safeNum(watchRow.low, 0);
    if (!safeNum(existing.refHigh, 0)) existing.refHigh = safeNum(watchRow.high, 0);
    evaluateHolding(existing, false);
  } else {
    const now = safeNum(watchRow.now, 0);
    const row = reactive({
      name: watchRow.name || watchRow.fullCode,
      fullCode: watchRow.fullCode,
      cost: 0,
      quantity: 0,
      ruleType: "r1",
      buyDate: todayStr(),
      swingLow: safeNum(watchRow.low, 0),
      refHigh: safeNum(watchRow.high, 0),
      now,
      close: safeNum(watchRow.close, now),
      highest: Math.max(now, 0),
      pnlRate: "0.00",
      stopLossTriggered: false,
      takeProfitTriggered: false,
      ruleSignalText: "持有",
      ruleSignalType: "success",
      monitorPrice: 0,
      monitorPriceText: "--",
      monitorDesc: "未激活",
      monitorStatus: "neutral"
    });
    evaluateHolding(row, false);
    holdingsData.value.unshift(row);
  }
  saveStateDebounced();
  ElMessage.success("已加入持仓");
};

const onFieldChange = (row, field) => {
  const isManual = isValidNumber(row[field]);
  if (field === "high") row.manualHigh = isManual;
  if (field === "low") row.manualLow = isManual;
  if (field === "avg") row.manualAvg = isManual;
  calculateRow(row);
};

const onHoldingFieldChange = (row) => evaluateHolding(row);
const onHoldingHighestChange = (row) => {
  row.highest = safeNum(row.highest, 0);
  evaluateHolding(row);
};
const removeItem = (row) => {
  const index = tableData.value.findIndex((x) => x.fullCode === row.fullCode);
  if (index < 0) return;
  tableData.value.splice(index, 1);
  saveStateDebounced();
  initRowDrag();
};

const removeHolding = (index) => {
  holdingsData.value.splice(index, 1);
  saveStateDebounced();
};

const togglePin = (row) => {
  const index = tableData.value.findIndex((x) => x.fullCode === row.fullCode);
  const item = tableData.value[index];
  if (!item) return;
  item.isPinned = !item.isPinned;
  const movedItem = tableData.value.splice(index, 1)[0];
  if (movedItem.isPinned) {
    tableData.value.unshift(movedItem);
  } else {
    const pinnedCount = tableData.value.filter((row) => row.isPinned).length;
    tableData.value.splice(pinnedCount, 0, movedItem);
  }
  saveStateDebounced();
  initRowDrag();
};

const moveToFront = (row) => {
  const index = tableData.value.findIndex((x) => x.fullCode === row.fullCode);
  const item = tableData.value[index];
  if (!item) return;
  const movedItem = tableData.value.splice(index, 1)[0];
  const pinnedCount = tableData.value.filter((row) => row.isPinned).length;
  tableData.value.splice(movedItem.isPinned ? 0 : pinnedCount, 0, movedItem);
  saveStateDebounced();
  initRowDrag();
};

const clearWatchlist = () => {
  ElMessageBox.confirm("确定清空观察列表吗？").then(() => {
    tableData.value = [];
    saveStateDebounced();
    initRowDrag();
  }).catch(() => {});
};

const clearHoldings = () => {
  ElMessageBox.confirm("确定清空持仓吗？").then(() => {
    holdingsData.value = [];
    saveStateDebounced();
  }).catch(() => {});
};

const getDayChangePct = (row) => {
  const now = safeNum(row?.now, 0);
  const close = safeNum(row?.close, 0);
  if (close <= 0 || now <= 0) return null;
  const pct = ((now - close) / close) * 100;
  const rounded = Math.round(pct * 100) / 100;
  return Object.is(rounded, -0) ? 0 : rounded;
};

const formatDayChangePct = (row) => {
  const pct = getDayChangePct(row);
  if (pct == null) return "--";
  if (pct > 0) return `+${pct.toFixed(2)}%`;
  return `${pct.toFixed(2)}%`;
};

const getDayChangeClass = (row) => {
  const pct = getDayChangePct(row);
  if (pct == null || pct === 0) return "price-flat";
  return pct > 0 ? "price-up" : "price-down";
};

const getMonitorClass = (row) => {
  const status = row?.monitorStatus || "neutral";
  if (status === "danger") return "monitor-danger";
  if (status === "warning") return "monitor-warning";
  if (status === "active") return "monitor-active";
  return "monitor-neutral";
};

const getProfitClass = (row) => (safeNum(row.pnlRate, 0) >= 0 ? "profit-up" : "profit-down");

const checkStorage = async () => {
  try {
    const [health, state] = await Promise.all([apiRequest("/health"), apiRequest("/state")]);
    const watchCount = (state.data?.watchlist || []).length;
    const holdCount = (state.data?.holdings || []).length;
    ElMessageBox.alert(
      `Python后端状态: 正常\n服务时间戳: ${health.ts}\n观察列表条数: ${watchCount}\n持仓条数: ${holdCount}`,
      "后端检测结果"
    );
  } catch (e) {
    ElMessage.error(`后端不可用：${e.message || e}`);
  }
};

const startAutoRefresh = () => {
  if (refreshTimer) clearInterval(refreshTimer);
  if (!autoRefreshEnabled.value) return;
  refreshTimer = setInterval(() => {
    if (!loading.value) refreshAllPrices();
  }, REFRESH_MS);
};

const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
};

const onAutoRefreshToggle = (enabled) => {
  if (enabled) {
    startAutoRefresh();
  } else {
    stopAutoRefresh();
  }
};

watch(watchCategoryFilter, () => {
  initRowDrag();
});

watch(allWatchCategories, (cats) => {
  if (watchCategoryFilter.value !== "__all__" && !cats.includes(watchCategoryFilter.value)) {
    watchCategoryFilter.value = "__all__";
  }
});

onMounted(async () => {
  await loadHolidayCalendar();
  await loadState();
  holdingsData.value.forEach((row) => evaluateHolding(row, false));
  initRowDrag();
  await refreshAllPrices();
  startAutoRefresh();
});

onBeforeUnmount(() => {
  stopAutoRefresh();
  if (saveTimer) clearTimeout(saveTimer);
  if (rowSortable) {
    rowSortable.destroy();
    rowSortable = null;
  }
});
</script>

<style>
body {
  background-color: #f0f2f5;
  margin: 0;
  padding: 12px;
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  height: 100vh;
  box-sizing: border-box;
  overflow: hidden;
}

#app {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.app-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.header-box {
  flex-shrink: 0;
  margin-bottom: 14px;
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-box h2 {
  margin: 0;
  color: #409eff;
  font-size: 22px;
}

.header-box p {
  margin: 5px 0 0;
  font-size: 13px;
  color: #909399;
}

.toolbar {
  flex-shrink: 0;
  margin-bottom: 15px;
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.section-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.el-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.el-tabs__content {
  flex: 1;
  min-height: 0;
}

.el-tab-pane {
  height: 100%;
}

.pane-wrap {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.table-wrap {
  flex: 1;
  min-height: 0;
}

.el-table .warning-row td.el-table__cell {
  background-color: #fffdf6 !important;
  background: linear-gradient(135deg, #fff3cc 0%, #fffaf0 36%, #ffffff 100%) !important;
  color: #8e7100 !important;
  border-bottom: 1px solid #efe2b5 !important;
}

.el-table .warning-row td.el-table__cell .el-input__wrapper,
.el-table .warning-row td.el-table__cell .el-select__wrapper {
  background-color: #fffaf0 !important;
  box-shadow: 0 0 0 1px #e2c676 inset !important;
}

.el-table .normal-row td.el-table__cell {
  background-color: #fffaf3 !important;
  color: #e6a23c !important;
}

.el-table .danger-row td.el-table__cell {
  background-color: #fff9e6 !important;
  background: linear-gradient(to right, #fff, #fff9e6) !important;
  color: #b28f00 !important;
  border-bottom: 1px solid #ffd04b !important;
}

.red-text { color: #f56c6c; font-weight: bold; }
.green-text { color: #67c23a; font-weight: bold; }
.fib-val { font-family: "Monaco", "Consolas", monospace; font-size: 13px; font-weight: bold; }
.fib-hit-382 { color: #e6a23c; }
.fib-hit-618 { color: #b28f00; }
.fib-hit-786 { color: #b28f00; }
.price-block { display: flex; flex-direction: column; line-height: 1.1; }
.price-now { font-weight: 800; font-size: 15px; }
.price-pct { font-size: 12px; font-weight: 700; margin-top: 2px; }
.price-up { color: #f56c6c; }
.price-down { color: #67c23a; }
.price-flat { color: #303133; }
.monitor-wrap { display: flex; flex-direction: column; line-height: 1.15; }
.monitor-price { font-weight: 700; font-size: 14px; }
.monitor-desc { font-size: 12px; margin-top: 2px; }
.monitor-danger { color: #f56c6c; }
.monitor-warning { color: #e6a23c; }
.monitor-active { color: #409eff; }
.monitor-neutral { color: #909399; }
.market-tag { font-size: 10px; padding: 0 4px; border-radius: 3px; margin-right: 4px; }
.drag-handle { cursor: move; color: #909399; font-size: 14px; margin-right: 6px; user-select: none; }
.op-wrap { display: flex; align-items: center; justify-content: center; gap: 6px; }
.op-actions { display: flex; flex-direction: column; align-items: flex-start; line-height: 1; }
.op-actions .el-button { margin: 0; height: 18px; line-height: 18px; padding: 0; }
.op-actions .el-button + .el-button { margin-left: 0; margin-top: 4px; }
.op-label { display: inline-block; width: 56px; text-align: left; }
.tag-sh { background: #fee; color: #f56c6c; border: 1px solid #fcc; }
.tag-sz { background: #eef5ff; color: #409eff; border: 1px solid #c6e2ff; }
.tag-hk { background: #f0f9eb; color: #67c23a; border: 1px solid #c2e7b0; }
.profit-up { color: #f56c6c; font-weight: 700; }
.profit-down { color: #67c23a; font-weight: 700; }
</style>
